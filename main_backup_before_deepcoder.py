"""
联盟拓荒者 - 营火主程序 (通过 Ollama 使用本地模型)
Phase 1: 增加反馈记录
"""
import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

load_dotenv()
logger.add("campfire.log", rotation="1 day", level="INFO")

from infrastructure.event_bus import bus
from infrastructure.logger import CampfireLogger
from infrastructure.feedback_store import FeedbackStore
from adapters.ui.cli_ui import CliUI

campfire = CampfireLogger()
feedback_store = FeedbackStore()

llm = None
last_response = ""   # 存储上一条助手回复

# Ollama 适配器
try:
    from adapters.llm.ollama_adapter import OllamaAdapter
    resp = requests.get("http://localhost:11434/api/tags", timeout=5)
    if resp.status_code == 200:
        llm = OllamaAdapter(model_name="mindchat")
        logger.info("✅ 使用 Ollama + MindChat 模型")
    else:
        raise Exception("Ollama 服务未就绪")
except Exception as e:
    logger.warning(f"Ollama 适配器不可用: {e}")

# 降级
if llm is None:
    try:
        from adapters.llm.openai_adapter import OpenAIAdapter
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "your_key_here":
            llm = OpenAIAdapter(api_key=api_key)
            logger.info("✅ 使用 OpenAI")
    except:
        pass

if llm is None:
    from adapters.llm.mock_adapter import MockAdapter
    llm = MockAdapter()
    logger.warning("⚠️ 使用模拟模式")

from core.services.intent_parser import IntentParser
from core.services.planner import Planner

intent_parser = IntentParser()
planner = Planner(llm)

def on_user_input(data):
    global last_response
    # 先解析意图
    intent = intent_parser.parse(data)
    
    # 如果是反馈意图，记录上一条回复的评分
    if intent.type == "feedback" and last_response:
        score = intent.entities.get("score")
        if score in (1, -1):
            feedback_store.add_feedback(data, last_response, score)
        # 反馈本身不产生新的回答，直接返回
        return
    
    # 记录用户输入
    campfire.log_user(data)
    # 调用规划器（传入意图）
    planner.plan(intent)

def on_plan_executed(response):
    global last_response
    last_response = response
    campfire.log_assistant(response)
    global ui
    ui.show_response(response)

bus.subscribe("user_input", on_user_input)
bus.subscribe("plan_executed", on_plan_executed)

if __name__ == "__main__":
    ui = CliUI()
    recent = campfire.get_recent_context(5)
    if recent:
        print("\n🔥 营火余温（最近对话）:\n", recent, "\n")
    ui.start()

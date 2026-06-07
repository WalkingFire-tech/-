"""
联盟拓荒者 - 营火主程序 (通过 Ollama 使用本地模型)
Phase 1: 增加对话记忆
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
from adapters.ui.cli_ui import CliUI

# 初始化营火日志
campfire = CampfireLogger()

llm = None

# 优先尝试 Ollama (MindChat)
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

# 降级 OpenAI
if llm is None:
    try:
        from adapters.llm.openai_adapter import OpenAIAdapter
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "your_key_here":
            llm = OpenAIAdapter(api_key=api_key)
            logger.info("✅ 使用 OpenAI")
    except:
        pass

# 最终降级模拟
if llm is None:
    from adapters.llm.mock_adapter import MockAdapter
    llm = MockAdapter()
    logger.warning("⚠️ 使用模拟模式")

from core.services.intent_parser import IntentParser
from core.services.planner import Planner

intent_parser = IntentParser()
planner = Planner(llm)

def on_user_input(data):
    # 记录用户输入
    campfire.log_user(data)
    intent = intent_parser.parse(data)
    planner.plan(intent)

def on_plan_executed(response):
    # 记录助手回复
    campfire.log_assistant(response)
    global ui
    ui.show_response(response)

bus.subscribe("user_input", on_user_input)
bus.subscribe("plan_executed", on_plan_executed)

if __name__ == "__main__":
    ui = CliUI()
    # 可选：启动时显示最近几条记忆
    recent = campfire.get_recent_context(5)
    if recent:
        print("\n🔥 营火余温（最近对话）:\n", recent, "\n")
    ui.start()

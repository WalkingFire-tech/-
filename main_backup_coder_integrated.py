"""
联盟拓荒者 - 营火主程序 (支持 DeepCoder 动态路由)
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

campfire = CampfireLogger()

# 模型适配器字典
adapters = {}

# 1. 检查 Ollama 服务
try:
    resp = requests.get("http://localhost:11434/api/tags", timeout=5)
    if resp.status_code != 200:
        raise Exception("Ollama 服务未响应")
except Exception as e:
    logger.error(f"Ollama 服务不可用: {e}")
    # 降级到模拟模式
    from adapters.llm.mock_adapter import MockAdapter
    adapters["default"] = MockAdapter()
    logger.warning("⚠️ 使用模拟模式")

if not adapters:
    from adapters.llm.ollama_adapter import OllamaAdapter

    # 添加 MindChat（心理/通用）
    try:
        adapters["mindchat"] = OllamaAdapter(model_name="mindchat")
        logger.info("✅ 加载 MindChat 模型")
    except Exception as e:
        logger.warning(f"MindChat 不可用: {e}")

    # 添加 DeepCoder（代码专用）
    try:
        # 检查 deepcoder 模型是否存在
        resp = requests.post("http://localhost:11434/api/generate", json={"model": "deepcoder", "stream": False}, timeout=5)
        if resp.status_code == 200:
            adapters["deepcoder"] = OllamaAdapter(model_name="deepcoder")
            logger.info("✅ 加载 DeepCoder 模型 (14B)")
        else:
            raise Exception("DeepCoder 模型未找到")
    except Exception as e:
        logger.warning(f"DeepCoder 不可用: {e}")

    # 如果没有可用模型，降级模拟
    if not adapters:
        from adapters.llm.mock_adapter import MockAdapter
        adapters["default"] = MockAdapter()
        logger.warning("⚠️ 无可用模型，使用模拟模式")

from core.services.intent_parser import IntentParser
from core.services.planner import Planner

intent_parser = IntentParser()
planner = Planner(adapters)

def on_user_input(data):
    campfire.log_user(data)
    intent = intent_parser.parse(data)
    planner.plan(intent)

def on_plan_executed(response):
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

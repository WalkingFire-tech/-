"""
联盟拓荒者 - 营火主程序 (支持轻量代码模型)
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
adapters = {}

try:
    resp = requests.get("http://localhost:11434/api/tags", timeout=5)
    if resp.status_code != 200:
        raise Exception("Ollama 服务未响应")
except Exception as e:
    logger.error(f"Ollama 服务不可用: {e}")
    from adapters.llm.mock_adapter import MockAdapter
    adapters["default"] = MockAdapter()

if not adapters:
    from adapters.llm.ollama_adapter import OllamaAdapter

    # MindChat (心理/通用)
    try:
        adapters["mindchat"] = OllamaAdapter(model_name="mindchat")
        logger.info("✅ 加载 MindChat")
    except Exception as e:
        logger.warning(f"MindChat 不可用: {e}")

    # 轻量代码模型 (优先)
    try:
        adapters["code_light"] = OllamaAdapter(model_name="qwen2.5-coder:1.5b")
        logger.info("✅ 加载轻量代码模型 qwen2.5-coder:1.5b")
    except Exception as e:
        logger.warning(f"轻量代码模型不可用: {e}")

    # DeepCoder 备选 (如果存在)
    try:
        adapters["deepcoder"] = OllamaAdapter(model_name="deepcoder")
        logger.info("✅ 加载 DeepCoder (备选)")
    except Exception as e:
        logger.warning(f"DeepCoder 不可用: {e}")

    if not adapters:
        from adapters.llm.mock_adapter import MockAdapter
        adapters["default"] = MockAdapter()

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

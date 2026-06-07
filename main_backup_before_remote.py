"""
联盟拓荒者 - 营火主程序 (支持本地+远程模型)
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
from infrastructure.model_stats import ModelStats
from infrastructure.experience_pool import ExperiencePool
from adapters.ui.cli_ui import CliUI

campfire = CampfireLogger()
adapters = {}

# 检查 Ollama 服务
try:
    resp = requests.get("http://localhost:11434/api/tags", timeout=5)
    if resp.status_code != 200:
        raise Exception("Ollama 服务未响应")
except Exception as e:
    logger.error(f"Ollama 服务不可用: {e}")

if not adapters:
    from adapters.llm.ollama_adapter import OllamaAdapter

    # MindChat
    try:
        adapters["mindchat"] = OllamaAdapter(model_name="mindchat")
        logger.info("✅ 加载 MindChat")
    except Exception as e:
        logger.warning(f"MindChat 不可用: {e}")

    # 轻量代码模型
    try:
        adapters["code_light"] = OllamaAdapter(model_name="qwen2.5-coder:1.5b")
        logger.info("✅ 加载轻量代码模型 qwen2.5-coder:1.5b")
    except Exception as e:
        logger.warning(f"轻量代码模型不可用: {e}")

    # DeepCoder 备选
    try:
        adapters["deepcoder"] = OllamaAdapter(model_name="deepcoder")
        logger.info("✅ 加载 DeepCoder (14B)")
    except Exception as e:
        logger.warning(f"DeepCoder 不可用: {e}")

# 远程模型（如果配置了 API Key）
try:
    from adapters.llm.remote_adapter import RemoteAdapter
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key != "your_key_here":
        adapters["remote_gpt4"] = RemoteAdapter(model_name="gpt-4o-mini")  # 或 gpt-3.5-turbo
        logger.info("✅ 加载远程模型 (GPT-4o-mini)")
    else:
        logger.warning("未配置 OPENAI_API_KEY，跳过远程模型")
except Exception as e:
    logger.warning(f"远程模型不可用: {e}")

# 确保至少有一个适配器
if not adapters:
    from adapters.llm.mock_adapter import MockAdapter
    adapters["default"] = MockAdapter()
    logger.warning("⚠️ 无可用模型，使用模拟模式")

from core.services.intent_parser import IntentParser
from core.services.planner import Planner

intent_parser = IntentParser()
planner = Planner(adapters)
exp_pool = ExperiencePool()

def on_user_input(data):
    campfire.log_user(data)
    intent = intent_parser.parse(data)

    if intent.type == "feedback":
        last_call = planner.get_last_call_info()
        if last_call and last_call["model"]:
            stats = ModelStats()
            stats.update_last_feedback(
                model_name=last_call["model"],
                task_type=last_call["task_type"],
                feedback=intent.entities.get("score", 0)
            )
            # 更新经验池中的反馈
            import sqlite3
            try:
                with sqlite3.connect("experience_pool.db") as conn:
                    conn.execute('''
                        UPDATE experiences
                        SET user_feedback = ?
                        WHERE id = (
                            SELECT id FROM experiences
                            WHERE model_name = ? AND intent_type = ?
                            ORDER BY timestamp DESC LIMIT 1
                        )
                    ''', (intent.entities.get("score", 0), last_call["model"], last_call["task_type"]))
            except Exception as e:
                logger.warning(f"更新经验池反馈失败: {e}")
            logger.info(f"反馈已记录: {last_call['model']} 在 {last_call['task_type']} 获得 {intent.entities.get('score')}")
            ui.show_response(f"👍 感谢反馈！已记录评分 {intent.entities.get('score')}")
        else:
            logger.warning("没有可用的最近调用信息")
            ui.show_response("⚠️ 暂时无法记录反馈，请稍后再试")
        return

    planner.plan(intent)

def on_plan_executed(response):
    campfire.log_assistant(response)
    global ui
    ui.show_response(response)

bus.subscribe("user_input", on_user_input)
bus.subscribe("plan_executed", on_plan_executed)

if __name__ == "__main__":
    import sqlite3
    ui = CliUI()
    recent = campfire.get_recent_context(5)
    if recent:
        print("\n🔥 营火余温（最近对话）:\n", recent, "\n")
    ui.start()

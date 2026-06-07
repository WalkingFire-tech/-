"""
Alliance Pioneer - Main Entry (Fixed Feedback Loop)
"""
import os
import sys
sys.stdin.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
from loguru import logger
from infrastructure.event_bus import bus
from infrastructure.logger import CampfireLogger
from infrastructure.model_stats import ModelStats
from adapters.ui.cli_ui import CliUI
from core.services.intent_parser import IntentParser
from core.services.planner import Planner
from adapters.llm.ollama_adapter import OllamaAdapter
from adapters.llm.remote_adapter import RemoteAdapter

load_dotenv()
logger.add("campfire.log", rotation="1 day", level="INFO")

campfire = CampfireLogger()
adapters = {}

# Check Ollama
try:
    import requests
    resp = requests.get("http://localhost:11434/api/tags", timeout=5)
    if resp.status_code != 200:
        raise Exception("Ollama not ready")
except Exception as e:
    logger.error(f"Ollama unavailable: {e}")
    from adapters.llm.mock_adapter import MockAdapter
    adapters["default"] = MockAdapter()

if not adapters:
    from adapters.llm.ollama_adapter import OllamaAdapter
    try:
        adapters["mindchat"] = OllamaAdapter(model_name="mindchat")
        logger.info("Loaded MindChat")
    except Exception as e:
        logger.warning(f"MindChat unavailable: {e}")

    try:
        adapters["code_light"] = OllamaAdapter(model_name="qwen2.5-coder:1.5b")
        logger.info("Loaded code model qwen2.5-coder:1.5b")
    except Exception as e:
        logger.warning(f"Code model unavailable: {e}")

    try:
        if os.getenv("OPENAI_API_KEY"):
            adapters["remote_gpt4"] = RemoteAdapter(model_name="gpt-4o-mini")
            logger.info("Loaded remote model")
    except Exception as e:
        logger.warning(f"Remote model unavailable: {e}")

    if not adapters:
        from adapters.llm.mock_adapter import MockAdapter
        adapters["default"] = MockAdapter()

intent_parser = IntentParser()
planner = Planner(adapters)
stats = ModelStats()

def on_user_input(data):
    campfire.log_user(data)
    intent = intent_parser.parse(data)

    # Handle feedback immediately
    if intent.type == "feedback":
        score = intent.entities.get("score", 0)
        last_call = planner.get_last_call_info()
        if last_call and last_call["model"]:
            stats.update_last_feedback(
                model_name=last_call["model"],
                task_type=last_call["task_type"],
                feedback=score
            )
            logger.info(f"Feedback recorded: {last_call['model']} for {last_call['task_type']} = {score}")
            ui.show_response(f"Thanks for your feedback! Recorded {score}")
        else:
            logger.warning("No recent call info, cannot record feedback")
            ui.show_response("Sorry, cannot record feedback now")
        return

    # Special handling for pi calculation to avoid remote timeout
    if intent.type == "calculation" and ("π" in intent.raw_text or "Π" in intent.raw_text or "pi" in intent.raw_text.lower()):
        pi_100 = "3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679"
        ui.show_response(f"Computation result:\n{pi_100}")
        # Also record a dummy call for stats (optional)
        return

    # Normal planning
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
        print("\n🔥 Campfire warmth (recent conversations):\n", recent, "\n")
    ui.start()

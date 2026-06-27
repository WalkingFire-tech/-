"""
Alliance Pioneer - Main Entry (Fixed Feedback Loop)
"""
import os
import sys
import signal
import atexit
sys.stdin.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
from loguru import logger
from infrastructure.event_bus import bus
from infrastructure.logger import CampfireLogger
from infrastructure.model_stats import ModelStats
from infrastructure.config_manager import config
from infrastructure.calculation_handler import CalculationHandler
from adapters.ui.cli_ui import CliUI
from core.services.intent_parser import IntentParser
from core.services.planner import Planner
from adapters.llm.ollama_adapter import OllamaAdapter
from adapters.llm.remote_adapter import RemoteAdapter

load_dotenv()
logger.add("campfire.log", rotation="1 day", level="INFO")

try:
    from infrastructure.database import init_all_databases
    init_all_databases()
except Exception as e:
    logger.warning(f"数据库初始化失败: {e}")

try:
    from infrastructure.vector_retriever import vector_retriever
    vector_retriever.load_index()
    logger.info("向量索引已加载")
except Exception as e:
    logger.debug(f"向量索引加载失败(首次运行): {e}")

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
            logger.info("Loaded remote GPT-4o-mini")
    except Exception as e:
        logger.warning(f"Remote GPT model unavailable: {e}")

    try:
        if os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"):
            adapters["deepseek-chat"] = RemoteAdapter(model_name="deepseek-chat")
            logger.info("Loaded DeepSeek Chat")
    except Exception as e:
        logger.warning(f"DeepSeek Chat unavailable: {e}")

    try:
        if os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"):
            adapters["deepseek-coder"] = RemoteAdapter(model_name="deepseek-coder")
            logger.info("Loaded DeepSeek Coder")
    except Exception as e:
        logger.warning(f"DeepSeek Coder unavailable: {e}")

    # 加载LoRA微调模型
    try:
        from adapters.llm.lora_adapter import create_lora_adapter
        adapters["closed_loop_lora"] = create_lora_adapter()
        logger.success("✓ LoRA微调模型已加载 (闭环进化能力)")
    except Exception as e:
        logger.warning(f"LoRA模型不可用: {e}")

    if not adapters:
        from adapters.llm.mock_adapter import MockAdapter
        adapters["default"] = MockAdapter()

intent_parser = IntentParser()
planner = Planner(adapters)
stats = ModelStats()

try:
    from meta.controller import get_meta_controller
    meta_controller = get_meta_controller()
    meta_controller.start_scheduler()
    logger.info("元控制层调度器已启动")
except Exception as e:
    logger.warning(f"元控制层启动失败: {e}")
    meta_controller = None

try:
    from infrastructure.config_watcher import config_watcher
    config_watcher.start()
    logger.info("配置文件监控已启动")
except Exception as e:
    logger.warning(f"配置监控启动失败: {e}")

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

    if intent.type == "calculation":
        calc_result = CalculationHandler.handle_calculation(intent.raw_text)
        if calc_result["success"]:
            ui.show_response(f"计算结果:\n{calc_result['result']}")
            return
        elif calc_result["error"]:
            ui.show_response(f"计算失败: {calc_result['error']}")
            return

    # Normal planning
    planner.plan(intent)

def on_plan_executed(response):
    campfire.log_assistant(response)
    global ui
    ui.show_response(response)

bus.subscribe("user_input", on_user_input)
bus.subscribe("plan_executed", on_plan_executed)


def on_optimize_request(data):
    """处理优化命令请求"""
    method = data.get("method", "bayesian")
    iterations = data.get("iterations", 15)
    
    if meta_controller:
        result = meta_controller.run_manual_optimization(
            method=method,
            n_iterations=iterations
        )
        
        if result.get("success"):
            ui.show_response(
                f"✓ 优化完成!\n"
                f"最佳得分: {result['best_score']:.4f}\n"
                f"最佳参数: {result['best_params']}"
            )
        else:
            ui.show_response(f"✗ 优化失败: {result.get('error')}")
    else:
        ui.show_response("元控制层未启动,无法优化")


def on_induction_request(data):
    """处理归纳命令请求"""
    days = data.get("days", 7)
    
    try:
        from meta.induction import induction_scheduler
        result = induction_scheduler.run_induction(days)
        
        if result.get("success"):
            ui.show_response(
                f"✓ 归纳完成!\n"
                f"发现模式: {result['patterns']}个\n"
                f"生成规则: {result['rules']}条"
            )
        else:
            ui.show_response(f"✗ 归纳失败: {result.get('message')}")
    except Exception as e:
        ui.show_response(f"✗ 归纳失败: {e}")


from infrastructure.events import Events
bus.subscribe(Events.CMD_OPTIMIZE, on_optimize_request)
bus.subscribe(Events.CMD_INDUCTION, on_induction_request)


def shutdown():
    """优雅关闭所有资源"""
    if hasattr(shutdown, '_called'):
        return
    shutdown._called = True
    
    logger.info("正在关闭系统...")
    
    try:
        from infrastructure.vector_retriever import vector_retriever
        vector_retriever.save_index()
        logger.info("向量索引已保存")
    except Exception as e:
        logger.debug(f"向量索引保存失败: {e}")
    
    try:
        from infrastructure.config_watcher import config_watcher
        config_watcher.stop()
        logger.info("配置监控已停止")
    except Exception as e:
        logger.warning(f"停止配置监控失败: {e}")
    
    if meta_controller:
        try:
            meta_controller.stop_scheduler()
            logger.info("元控制层调度器已停止")
        except Exception as e:
            logger.warning(f"停止调度器失败: {e}")
    
    try:
        from infrastructure.db_pool import close_all_pools
        close_all_pools()
    except Exception as e:
        logger.debug(f"关闭连接池失败: {e}")
    
    logger.info("系统已安全关闭")


def signal_handler(sig, frame):
    """处理Ctrl+C等退出信号"""
    print("\n收到退出信号,正在清理...")
    shutdown()
    sys.exit(0)


atexit.register(shutdown)
signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    ui = CliUI()
    recent = campfire.get_recent_context(5)
    if recent:
        print("\n🔥 Campfire warmth (recent conversations):\n", recent, "\n")
    
    try:
        ui.start()
    except KeyboardInterrupt:
        logger.info("收到键盘中断")
    finally:
        shutdown()

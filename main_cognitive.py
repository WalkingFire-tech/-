"""
联盟拓荒者 - 认知系统入口

这是整个系统的启动入口，让同行者真正"走起来"。
"""

import sys
import signal
import time
from pathlib import Path
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))

from core.services.cognitive_planner import get_cognitive_planner


def setup_logging():
    """配置日志"""
    try:
        logger.remove()
        logger.add(
            sys.stdout,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level="INFO"
        )
        
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logger.add(
            "logs/cognitive_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            level="DEBUG"
        )
    except:
        pass


def signal_handler(sig, frame):
    """信号处理"""
    logger.info("\n🛑 收到停止信号，正在关闭系统...")
    try:
        planner = get_cognitive_planner()
        planner.shutdown()
    except Exception as e:
        logger.error(f"关闭系统失败: {e}")
    sys.exit(0)


def main():
    """主函数"""
    setup_logging()
    
    logger.info("=" * 60)
    logger.info("🔥 联盟拓荒者 (Alliance Pioneer)")
    logger.info("  一个会思考的同行者 | A Thinking Companion")
    logger.info("=" * 60)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 正在启动系统...")
    planner = get_cognitive_planner()
    
    status = planner.get_system_status()
    logger.info(f"✅ 系统已启动 (会话数: {status['conversation_count']})")
    
    relationship = status.get('relationship', {})
    logger.info(f"   关系: 信任={relationship.get('trust', 0.5):.2f}, "
                f"亲密={relationship.get('intimacy', 0.0):.2f}")
    
    goals = status.get('goals', [])
    if goals:
        logger.info(f"   进化目标: {[g.get('dimension', 'unknown') for g in goals]}")
    
    logger.info("")
    logger.info("📝 系统正在运行，输入 'exit' 退出")
    logger.info("-" * 60)
    
    while True:
        try:
            user_input = input("\n你: ")
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                logger.info("👋 再见！")
                break
            
            if user_input.lower() in ['status', 'stats']:
                status = planner.get_system_status()
                logger.info(f"📊 系统状态: {status['status']}")
                logger.info(f"   对话数: {status['conversation_count']}")
                relationship = status.get('relationship', {})
                logger.info(f"   关系: 信任={relationship.get('trust', 0.5):.2f}")
                continue
            
            if user_input.lower() == 'components':
                status = planner.get_system_status()
                components = status.get('components', {})
                logger.info("📦 组件状态:")
                for name, running in components.items():
                    status_str = "✅ 运行中" if running else "❌ 已停止"
                    logger.info(f"   {name}: {status_str}")
                continue
            
            if not user_input.strip():
                continue
            
            result = planner.process(user_input)
            
            print(f"\n拓荒者: {result.response}")
            
            if result.processing_time_ms > 100:
                logger.debug(f"⏱️ 处理时间: {result.processing_time_ms:.0f}ms")
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"处理异常: {e}")
    
    planner.shutdown()
    logger.info("🛑 系统已关闭")


if __name__ == "__main__":
    main()
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from core.ports.ui_port import UIPort
from infrastructure.event_bus import bus
from loguru import logger

class CliUI(UIPort):
    def __init__(self):
        self.console = Console()
        self.running = True
    
    def start(self):
        """启动交互循环"""
        self.console.print(Panel.fit("🔥 联盟拓荒者 - 营火已点燃", style="bold green"))
        self.console.print("输入你的问题，按 Ctrl+C 或输入 'exit' 退出\n")
        
        while self.running:
            try:
                user_input = Prompt.ask("[bold cyan]你[/]")
                if user_input.lower() in ("exit", "quit"):
                    self.running = False
                    self.console.print("[yellow]营火暂时熄灭，随时回来添柴。[/]")
                    break
                # 发布用户输入事件
                bus.publish("user_input", user_input)
            except KeyboardInterrupt:
                self.running = False
                self.console.print("\n[yellow]再见，拓荒者。[/]")
                break
            except Exception as e:
                logger.error(f"UI 错误: {e}")
    
    def show_response(self, text: str):
        """显示系统的回复"""
        self.console.print(Panel(text, title="🤖 拓荒者", border_style="blue"))

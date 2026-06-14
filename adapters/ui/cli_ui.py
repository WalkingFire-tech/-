"""
增强的CLI UI - 支持多行输入和文件输入
"""
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from pathlib import Path
from core.ports.ui_port import UIPort
from infrastructure.event_bus import bus
from loguru import logger


class EnhancedCliUI(UIPort):
    """增强的CLI界面"""
    
    def __init__(self):
        self.console = Console()
        self.running = True
        self.multiline_mode = False
        self.multiline_buffer = []
        
        # 文件输入适配器
        try:
            from adapters.input.file_adapter import file_adapter
            self.file_adapter = file_adapter
        except:
            self.file_adapter = None
    
    def start(self):
        """启动交互循环"""
        self.console.print(Panel.fit(
            "[bold green]🔥 联盟拓荒者 - 营火已点燃[/]\n\n"
            "[cyan]命令:[/]\n"
            "  [yellow]:ml[/] 或 [yellow]:multiline[/] - 进入多行输入模式\n"
            "  [yellow]:file <路径>[/] - 输入文件\n"
            "  [yellow]:folder <路径>[/] - 输入文件夹\n"
            "  [yellow]:help[/] - 显示帮助\n"
            "  [yellow]exit/quit[/] - 退出",
            style="bold"
        ))
        
        while self.running:
            try:
                # 多行模式
                if self.multiline_mode:
                    user_input = self._handle_multiline()
                else:
                    # 单行模式
                    user_input = Prompt.ask("[bold cyan]你[/]")
                
                # 处理命令
                if user_input.startswith(':'):
                    self._handle_command(user_input)
                    continue
                
                # 退出命令
                if user_input.lower() in ("exit", "quit"):
                    self.running = False
                    self.console.print("[yellow]营火暂时熄灭,随时回来添柴。[/]")
                    break
                
                # 发布用户输入事件
                if user_input.strip():
                    bus.publish("user_input", user_input)
                    
            except KeyboardInterrupt:
                if self.multiline_mode:
                    # Ctrl+C退出多行模式
                    self.multiline_mode = False
                    self.multiline_buffer = []
                    self.console.print("\n[yellow]已退出多行模式[/]")
                else:
                    self.running = False
                    self.console.print("\n[yellow]再见,拓荒者。[/]")
                    break
            except Exception as e:
                logger.error(f"UI错误: {e}")
    
    def _handle_multiline(self) -> str:
        """处理多行输入"""
        self.console.print("[bold green]多行输入模式 (输入 :end 结束, Ctrl+C 取消)[/]")
        
        lines = []
        line_num = 1
        
        while True:
            try:
                line = Prompt.ask(f"[dim]{line_num:3d}[/]")
                
                if line.strip() == ":end":
                    break
                
                lines.append(line)
                line_num += 1
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]已取消多行输入[/]")
                return ""
        
        content = "\n".join(lines)
        self.multiline_mode = False
        
        self.console.print(f"[green]✓ 已输入 {len(lines)} 行,共 {len(content)} 字符[/]")
        
        return content
    
    def _handle_command(self, command: str):
        """处理命令"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else None
        
        if cmd in (":ml", ":multiline"):
            self.multiline_mode = True
            self.console.print("[cyan]进入多行输入模式...[/]")
            
        elif cmd == ":file":
            if not args:
                self.console.print("[red]请指定文件路径: :file <路径>[/]")
                return
            
            if not self.file_adapter:
                self.console.print("[red]文件输入功能未加载[/]")
                return
            
            file_path = args.strip()
            result = self.file_adapter.on_file_selected(file_path)
            
            if result['success']:
                self.console.print(f"[green]✓ 文件已加载: {result['event']['filename']}[/]")
            else:
                self.console.print(f"[red]✗ 加载失败: {result.get('error')}[/]")
        
        elif cmd == ":folder":
            if not args:
                self.console.print("[red]请指定文件夹路径: :folder <路径>[/]")
                return
            
            if not self.file_adapter:
                self.console.print("[red]文件输入功能未加载[/]")
                return
            
            folder_path = args.strip()
            result = self.file_adapter.on_folder_selected(folder_path, recursive=False)
            
            if result['success']:
                self.console.print(f"[green]✓ 文件夹已加载: {result['event']['file_count']} 个文件[/]")
            else:
                self.console.print(f"[red]✗ 加载失败: {result.get('error')}[/]")
        
        elif cmd == ":learning":
            self._handle_learning_command(args)
        
        elif cmd == ":privacy":
            self._handle_privacy_command(args)
        
        elif cmd == ":optimize":
            self._handle_optimize_command(args)
        
        elif cmd == ":induction":
            self._handle_induction_command(args)
        
        elif cmd == ":conflict":
            self._handle_conflict_command(args)
        
        elif cmd == ":tools":
            self._handle_tools_command(args)
        
        elif cmd == ":watch":
            self._handle_watch_command(args)
        
        elif cmd == ":plan":
            self._handle_plan_command(args)
        
        elif cmd == ":help":
            self._show_help()
        
        else:
            self.console.print(f"[yellow]未知命令: {cmd}[/]")
    
    def _handle_learning_command(self, args: str):
        """处理学习命令"""
        if not args:
            self.console.print("[yellow]学习命令用法:[/]")
            self.console.print("  :learning list - 列出学习规则")
            self.console.print("  :learning stats - 显示统计")
            self.console.print("  :learning rollback [n] - 回滚n次")
            self.console.print("  :learning cleanup - 清理过期规则")
            self.console.print("  :learning log - 查看学习活动日志")
            self.console.print("  :learning knowledge [topic] - 查看已学习知识")
            self.console.print("  :learning pause - 暂停学习")
            self.console.print("  :learning resume - 恢复学习")
            return
        
        try:
            from meta.learning_safety import learning_safety
            
            parts = args.split()
            sub_cmd = parts[0]
            
            if sub_cmd == "list":
                rules = learning_safety.get_active_rules()
                self.console.print(f"[cyan]活跃学习规则 ({len(rules)}条):[/]")
                for i, rule in enumerate(rules[:10], 1):
                    conf = rule.get_effective_confidence()
                    fixed = "🔒" if rule.is_fixed else ""
                    self.console.print(f"  {i}. {rule.pattern[:30]} -> {rule.intent_type} ({conf:.2f}) {fixed}")
            
            elif sub_cmd == "stats":
                stats = learning_safety.get_stats()
                self.console.print(f"[cyan]学习统计:[/]")
                self.console.print(f"  总规则数: {stats['total_rules']}")
                self.console.print(f"  固定规则: {stats['fixed_rules']}")
                self.console.print(f"  活跃规则: {stats['active_rules']}")
                self.console.print(f"  平均置信度: {stats['avg_confidence']:.2f}")
            
            elif sub_cmd == "rollback":
                steps = int(parts[1]) if len(parts) > 1 else 1
                result = learning_safety.rollback(steps)
                if result['success']:
                    self.console.print(f"[green]✓ 回滚成功: {result['count']}次[/]")
                else:
                    self.console.print("[red]✗ 回滚失败[/]")
            
            elif sub_cmd == "cleanup":
                cleaned = learning_safety.cleanup_expired_rules()
                self.console.print(f"[green]✓ 清理{cleaned}条过期规则[/]")
            
            elif sub_cmd == "log":
                try:
                    from infrastructure.active_learner import active_learner
                    activities = active_learner.get_activities(limit=10)
                    self.console.print(f"[cyan]学习活动日志 ({len(activities)}条):[/]")
                    for act in activities:
                        status_color = "green" if act['status'] == "completed" else "yellow"
                        self.console.print(f"  [{status_color}]{act['id']}[/{status_color}] {act['trigger']} - {act['query'][:30]} ({act['status']})")
                except Exception as e:
                    self.console.print(f"[red]获取学习日志失败: {e}[/]")
            
            elif sub_cmd == "knowledge":
                try:
                    from infrastructure.active_learner import active_learner
                    topic = parts[1] if len(parts) > 1 else None
                    knowledge = active_learner.get_knowledge(topic=topic, limit=10)
                    self.console.print(f"[cyan]已学习知识 ({len(knowledge)}条):[/]")
                    for k in knowledge:
                        self.console.print(f"  {k['id']}. {k['topic'][:40]} (有用性: {k['usefulness_score']:.2f})")
                except Exception as e:
                    self.console.print(f"[red]获取知识失败: {e}[/]")
            
            elif sub_cmd == "pause":
                try:
                    from infrastructure.active_learner import active_learner
                    active_learner.pause()
                    self.console.print("[yellow]学习器已暂停[/]")
                except Exception as e:
                    self.console.print(f"[red]暂停失败: {e}[/]")
            
            elif sub_cmd == "resume":
                try:
                    from infrastructure.active_learner import active_learner
                    active_learner.resume()
                    self.console.print("[green]学习器已恢复[/]")
                except Exception as e:
                    self.console.print(f"[red]恢复失败: {e}[/]")
            
            else:
                self.console.print(f"[yellow]未知子命令: {sub_cmd}[/]")
        
        except Exception as e:
            self.console.print(f"[red]学习命令失败: {e}[/]")
    
    def _handle_privacy_command(self, args: str):
        """处理隐私命令"""
        if not args:
            self.console.print("[yellow]隐私命令用法:[/]")
            self.console.print("  :privacy summary - 数据摘要")
            self.console.print("  :privacy export - 导出数据")
            self.console.print("  :privacy forget - 遗忘数据(需确认)")
            return
        
        try:
            from meta.privacy_manager import privacy_manager
            
            parts = args.split()
            sub_cmd = parts[0]
            
            if sub_cmd == "summary":
                summary = privacy_manager.get_data_summary()
                self.console.print(f"[cyan]数据摘要:[/]")
                self.console.print(f"  数据目录: {summary['data_dir']}")
                self.console.print(f"  总大小: {summary['total_size_mb']:.2f} MB")
                self.console.print(f"  文件数: {sum(1 for f in summary['files'].values() if f['exists'])}")
            
            elif sub_cmd == "export":
                result = privacy_manager.export_data()
                if result['success']:
                    self.console.print(f"[green]✓ 数据已导出: {result['export_file']}[/]")
                else:
                    self.console.print(f"[red]✗ 导出失败: {result.get('error')}[/]")
            
            elif sub_cmd == "forget":
                if len(parts) > 1 and parts[1] == "confirm":
                    result = privacy_manager.forget_me(confirm=True)
                    if result['success']:
                        self.console.print(f"[green]✓ {result['message']}[/]")
                    else:
                        self.console.print(f"[red]✗ {result.get('error')}[/]")
                else:
                    self.console.print("[yellow]⚠️  这将删除所有学习数据![/]")
                    self.console.print("[yellow]确认请输入: :privacy forget confirm[/]")
            
            else:
                self.console.print(f"[yellow]未知子命令: {sub_cmd}[/]")
        
        except Exception as e:
            self.console.print(f"[red]隐私命令失败: {e}[/]")
    
    def _handle_optimize_command(self, args: str):
        """处理优化命令(通过事件总线)"""
        if not args:
            self.console.print("[yellow]优化命令用法:[/]")
            self.console.print("  :optimize run [n] - 运行n次优化(默认20)")
            self.console.print("  :optimize grid - 网格搜索")
            self.console.print("  :optimize random - 随机搜索")
            self.console.print("  :optimize suggest - 查看优化建议")
            return
        
        try:
            from infrastructure.event_bus import bus
            from infrastructure.events import Events
            
            parts = args.split()
            sub_cmd = parts[0]
            
            if sub_cmd == "run":
                n_iter = int(parts[1]) if len(parts) > 1 else 20
                self.console.print(f"[cyan]提交优化请求({n_iter}次迭代)...[/]")
                
                bus.publish(Events.CMD_OPTIMIZE, {
                    "method": "bayesian",
                    "iterations": n_iter
                })
            
            elif sub_cmd == "grid":
                self.console.print("[cyan]提交网格搜索请求...[/]")
                
                bus.publish(Events.CMD_OPTIMIZE, {
                    "method": "grid",
                    "iterations": 20
                })
            
            elif sub_cmd == "random":
                self.console.print("[cyan]提交随机搜索请求...[/]")
                
                bus.publish(Events.CMD_OPTIMIZE, {
                    "method": "random",
                    "iterations": 30
                })
            
            elif sub_cmd == "suggest":
                from meta.bayesian_optimizer import bayesian_optimizer
                suggestions = bayesian_optimizer.get_param_suggestions()
                
                self.console.print("[cyan]参数优化建议:[/]")
                for param, (value, suggestion) in suggestions.items():
                    self.console.print(f"  {param}: {value:.3f} - {suggestion}")
            
            else:
                self.console.print(f"[yellow]未知子命令: {sub_cmd}[/]")
        
        except Exception as e:
            self.console.print(f"[red]优化命令失败: {e}[/]")
    
    def _handle_induction_command(self, args: str):
        """处理归纳命令"""
        if not args:
            self.console.print("[yellow]归纳命令用法:[/]")
            self.console.print("  :induction run [days] - 运行归纳(默认7天)")
            self.console.print("  :induction status - 查看归纳状态")
            return
        
        try:
            from meta.controller import get_meta_controller
            from meta.induction import induction_scheduler
            
            parts = args.split()
            sub_cmd = parts[0]
            
            if sub_cmd == "run":
                days = int(parts[1]) if len(parts) > 1 else 7
                self.console.print(f"[cyan]开始归纳总结(最近{days}天)...[/]")
                
                result = induction_scheduler.run_induction(days)
                
                if result.get("success"):
                    self.console.print(f"[green]✓ 归纳完成[/]")
                    self.console.print(f"  发现模式: {result['patterns']}个")
                    self.console.print(f"  生成规则: {result['rules']}条")
                    if result.get("conflicts"):
                        self.console.print(f"  检测冲突: {result['conflicts']}个(已自动解决)")
                else:
                    self.console.print(f"[red]✗ 归纳失败: {result.get('message')}[/]")
            
            elif sub_cmd == "status":
                controller = get_meta_controller()
                status = controller.get_status()
                
                self.console.print("[cyan]元控制层状态:[/]")
                self.console.print(f"  调度器运行: {'是' if status['scheduler_active'] else '否'}")
                self.console.print(f"  当前参数: {status.get('current_params', {})}")
            
            else:
                self.console.print(f"[yellow]未知子命令: {sub_cmd}[/]")
        
        except Exception as e:
            self.console.print(f"[red]归纳命令失败: {e}[/]")
    
    def _handle_conflict_command(self, args: str):
        """处理冲突检测命令"""
        if not args:
            self.console.print("[yellow]冲突检测命令用法:[/]")
            self.console.print("  :conflict detect - 检测所有冲突")
            self.console.print("  :conflict resolve - 自动解决冲突")
            return
        
        try:
            from meta.conflict_detector import conflict_detector
            
            parts = args.split()
            sub_cmd = parts[0]
            
            if sub_cmd == "detect":
                report = conflict_detector.get_conflict_report()
                
                self.console.print(f"[cyan]冲突检测报告:[/]")
                self.console.print(f"  总冲突数: {report['total_conflicts']}")
                self.console.print(f"  模型冲突: {report['summary']['model_conflicts']}")
                self.console.print(f"  偏好冲突: {report['summary']['preference_conflicts']}")
                
                if report['conflicts']:
                    self.console.print("\n[yellow]冲突详情:[/]")
                    for i, conflict in enumerate(report['conflicts'][:5], 1):
                        self.console.print(f"  {i}. 规则{conflict['rule1_id']} vs 规则{conflict['rule2_id']}")
                        self.console.print(f"     类型: {conflict['conflict_type']}")
                        self.console.print(f"     建议: {conflict['suggestion']}")
            
            elif sub_cmd == "resolve":
                report = conflict_detector.get_conflict_report()
                
                if report['total_conflicts'] == 0:
                    self.console.print("[green]✓ 无冲突需要解决[/]")
                    return
                
                resolved = 0
                for conflict in report['conflicts']:
                    result = conflict_detector.resolve_conflict(conflict, resolution="auto")
                    if result.get("success"):
                        resolved += 1
                
                self.console.print(f"[green]✓ 已解决{resolved}个冲突[/]")
            
            else:
                self.console.print(f"[yellow]未知子命令: {sub_cmd}[/]")
        
        except Exception as e:
            self.console.print(f"[red]冲突检测命令失败: {e}[/]")
    
    def _handle_tools_command(self, args: str):
        """处理工具生成命令"""
        if not args:
            self.console.print("[yellow]工具生成命令用法:[/]")
            self.console.print("  :tools list - 列出生成的工具")
            self.console.print("  :tools analyze <失败描述> - 分析是否需要新工具")
            return
        
        try:
            from tools.registry import registry
            from pathlib import Path
            
            parts = args.split(maxsplit=1)
            sub_cmd = parts[0]
            
            if sub_cmd == "list":
                generated_dir = Path("tools/generated")
                
                if not generated_dir.exists():
                    self.console.print("[yellow]尚未生成任何工具[/]")
                    return
                
                tool_files = list(generated_dir.glob("*.py"))
                self.console.print(f"[cyan]已生成工具 ({len(tool_files)}个):[/]")
                
                for tool_file in tool_files:
                    self.console.print(f"  - {tool_file.stem}")
            
            elif sub_cmd == "analyze":
                if len(parts) < 2:
                    self.console.print("[red]请提供失败描述[/]")
                    return
                
                from core.services.planner import planner
                
                if not planner.tool_generator:
                    self.console.print("[red]工具生成器未激活[/]")
                    return
                
                failure_desc = parts[1]
                failure_context = {
                    "task_type": "custom",
                    "user_input": failure_desc,
                    "failure_reason": "手动分析"
                }
                
                result = planner.tool_generator.analyze_need_for_new_tool(failure_context)
                
                if result:
                    self.console.print(f"[green]✓ 建议创建新工具:[/]")
                    self.console.print(f"  名称: {result.get('tool_name')}")
                    self.console.print(f"  描述: {result.get('description')}")
                    self.console.print(f"  类别: {result.get('category')}")
                    self.console.print(f"  理由: {result.get('reasoning')}")
                else:
                    self.console.print("[yellow]不建议创建新工具[/]")
            
            else:
                self.console.print(f"[yellow]未知子命令: {sub_cmd}[/]")
        
        except Exception as e:
            self.console.print(f"[red]工具命令失败: {e}[/]")
    
    def _handle_watch_command(self, args: str):
        """处理目录监控命令"""
        if not args:
            self.console.print("[yellow]目录监控命令用法:[/]")
            self.console.print("  :watch start <目录> - 开始监控目录")
            self.console.print("  :watch stop - 停止所有监控")
            self.console.print("  :watch status - 查看监控状态")
            self.console.print("  :watch list - 列出监控的目录")
            return
        
        try:
            from infrastructure.directory_monitor import directory_monitor, create_default_file_handler
            
            parts = args.split(maxsplit=1)
            sub_cmd = parts[0]
            
            if sub_cmd == "start":
                if len(parts) < 2:
                    self.console.print("[red]请指定监控目录[/]")
                    return
                
                directory = parts[1].strip()
                handler = create_default_file_handler()
                
                result = directory_monitor.watch_directory(
                    directory,
                    on_created=handler,
                    on_modified=handler,
                    file_patterns=["*.py", "*.txt", "*.md", "*.json"]
                )
                
                if result.get("success"):
                    if not directory_monitor.status()["running"]:
                        directory_monitor.start()
                    
                    self.console.print(f"[green]✓ {result['message']}[/]")
                    self.console.print(f"  监控ID: {result['watch_id']}")
                else:
                    self.console.print(f"[red]✗ {result.get('message')}[/]")
            
            elif sub_cmd == "stop":
                directory_monitor.stop()
                self.console.print("[green]✓ 目录监控已停止[/]")
            
            elif sub_cmd == "status":
                status = directory_monitor.status()
                
                self.console.print("[cyan]目录监控状态:[/]")
                self.console.print(f"  可用: {'是' if status['available'] else '否'}")
                self.console.print(f"  运行中: {'是' if status['running'] else '否'}")
                self.console.print(f"  监控目录数: {status['watched_directories']}")
            
            elif sub_cmd == "list":
                watched = directory_monitor.list_watched()
                
                if not watched:
                    self.console.print("[yellow]尚未监控任何目录[/]")
                    return
                
                self.console.print(f"[cyan]监控的目录 ({len(watched)}个):[/]")
                for item in watched:
                    self.console.print(f"  - {item['directory']}")
                    self.console.print(f"    ID: {item['watch_id']}, 递归: {item['recursive']}")
            
            else:
                self.console.print(f"[yellow]未知子命令: {sub_cmd}[/]")
        
        except Exception as e:
            self.console.print(f"[red]监控命令失败: {e}[/]")
    
    def _handle_plan_command(self, args: str):
        """处理计划命令 - 进入认知模式"""
        try:
            from infrastructure.cognitive_layer import cognitive_layer
            from core.services.intent_parser import IntentParser
            
            if args:
                user_input = args
            else:
                self.console.print("[cyan]请输入要分析的问题：[/]")
                user_input = Prompt.ask("问题")
            
            if not user_input.strip():
                self.console.print("[yellow]请提供要分析的问题[/]")
                return
            
            parser = IntentParser()
            intent = parser.parse(user_input)
            
            self.console.print(f"[dim]分析意图: {intent.type}[/]")
            
            analysis = cognitive_layer.analyze(intent.raw_text, intent.type, "")
            report = cognitive_layer.generate_report(analysis)
            
            self.console.print(Panel(report, title="📋 逻辑分析报告", border_style="green"))
            
            subtasks = cognitive_layer.plan_from_analysis(analysis)
            if subtasks:
                self.console.print(f"\n[cyan]生成了 {len(subtasks)} 个可执行子任务[/]")
                for i, task in enumerate(subtasks, 1):
                    self.console.print(f"  {i}. [{task['type']}] {task['description']}")
        
        except Exception as e:
            self.console.print(f"[red]计划命令失败: {e}[/]")
    
    def _show_help(self):
        """显示帮助"""
        help_text = """
[bold cyan]联盟拓荒者 - 命令帮助[/]

[yellow]输入模式:[/]
  普通输入 - 直接输入文本,按回车发送
  :ml / :multiline - 进入多行输入模式
                     输入 :end 结束
                     Ctrl+C 取消

[yellow]文件输入:[/]
  :file <路径> - 加载单个文件
  :folder <路径> - 加载文件夹

[yellow]参数优化:[/]
  :optimize run [n] - 运行贝叶斯优化
  :optimize grid - 网格搜索
  :optimize random - 随机搜索
  :optimize suggest - 查看优化建议

[yellow]归纳总结:[/]
  :induction run [days] - 运行归纳总结
  :induction status - 查看归纳状态

[yellow]冲突检测:[/]
  :conflict detect - 检测规则冲突
  :conflict resolve - 自动解决冲突

[yellow]工具生成:[/]
  :tools list - 列出生成的工具
  :tools analyze <描述> - 分析是否需要新工具

[yellow]目录监控:[/]
  :watch start <目录> - 开始监控目录
  :watch stop - 停止所有监控
  :watch status - 查看监控状态
  :watch list - 列出监控的目录

[yellow]认知分析:[/]
  :plan [问题] - 进入认知模式，生成逻辑分析报告

[yellow]学习管理:[/]
  :learning list - 列出学习规则
  :learning stats - 显示统计
  :learning rollback [n] - 回滚n次
  :learning cleanup - 清理过期规则

[yellow]隐私控制:[/]
  :privacy summary - 数据摘要
  :privacy export - 导出数据
  :privacy forget - 遗忘数据

[yellow]其他命令:[/]
  :help - 显示此帮助
  exit / quit - 退出程序

[yellow]反馈:[/]
  +1 - 对上次回答点赞
  -1 - 对上次回答踩
"""
        self.console.print(Panel(help_text, border_style="cyan"))
    
    def show_response(self, text: str):
        """显示系统的回复"""
        self.console.print(Panel(text, title="🤖 拓荒者", border_style="blue"))


# 向后兼容
CliUI = EnhancedCliUI

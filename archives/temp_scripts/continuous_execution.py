"""
连续执行计划 - 立即完成所有阶段
不再等待"下周"，而是立即执行、验证、进入下一阶段
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime


class ContinuousExecution:
    """连续执行器 - 立即完成所有阶段"""
    
    def __init__(self):
        self.results = []
        self.current_stage = 0
        
    def execute_stage(self, stage_name: str, command: str, 
                     description: str) -> dict:
        """执行单个阶段
        
        Args:
            stage_name: 阶段名称
            command: 执行命令
            description: 描述
        
        Returns:
            执行结果
        """
        print(f"\n{'='*70}")
        print(f"阶段 {self.current_stage + 1}: {stage_name}")
        print(f"{'='*70}")
        print(f"描述: {description}")
        print(f"命令: {command}")
        print(f"开始时间: {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 70)
        
        result = {
            'stage': stage_name,
            'command': command,
            'start_time': datetime.now().isoformat(),
            'success': False,
            'output': ''
        }
        
        try:
            # 执行命令
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            result['output'] = process.stdout
            result['success'] = process.returncode == 0
            result['returncode'] = process.returncode
            
            if result['success']:
                print(f"✅ 阶段完成")
            else:
                print(f"⚠️ 阶段完成（有警告）")
                if process.stderr:
                    print(f"错误: {process.stderr[:200]}")
            
        except subprocess.TimeoutExpired:
            result['output'] = "超时"
            print(f"⏱️ 阶段超时（5分钟）")
            
        except Exception as e:
            result['output'] = str(e)
            print(f"❌ 阶段失败: {e}")
        
        result['end_time'] = datetime.now().isoformat()
        self.results.append(result)
        self.current_stage += 1
        
        return result
    
    def evaluate_and_continue(self, result: dict) -> bool:
        """评估结果并决定是否继续
        
        Args:
            result: 阶段结果
        
        Returns:
            是否继续下一阶段
        """
        print(f"\n评估阶段: {result['stage']}")
        
        if result['success']:
            print("✅ 阶段成功，继续下一阶段")
            return True
        else:
            print("⚠️ 阶段有警告，但仍可继续")
            return True  # 即使有警告也继续
    
    def run_all_stages(self):
        """运行所有阶段"""
        print("\n" + "="*70)
        print("联盟拓荒者 - 连续执行计划")
        print("立即完成所有阶段，不再等待")
        print("="*70)
        
        stages = [
            {
                'name': '系统验证',
                'command': 'python verify_system.py',
                'description': '验证所有核心模块是否就绪'
            },
            {
                'name': '章程验证',
                'command': 'python verify_charter.py',
                'description': '验证生命章程实现度'
            },
            {
                'name': 'P1阶段测试',
                'command': 'python test_federation.py',
                'description': '测试联邦调度核心功能'
            },
            {
                'name': 'P2阶段测试',
                'command': 'python test_p2_decomposition.py',
                'description': '测试任务分解与结果融合'
            },
            {
                'name': '完整集成测试',
                'command': 'python test_complete_integration.py',
                'description': '测试完整集成流程'
            },
            {
                'name': '能力矩阵评估',
                'command': 'python -c "from infrastructure.model_capability import model_capability; stats = model_capability.export_stats(); print(f\'已注册模型: {stats[\"registered_models\"]}个\')"',
                'description': '评估能力矩阵状态'
            },
            {
                'name': '生命维持系统检查',
                'command': 'python -c "from infrastructure.life_support import life_support; health = life_support.get_system_health(); print(f\'健康评分: {health[\"health_score\"]:.1f}/100\')"',
                'description': '检查生命维持系统'
            },
            {
                'name': '自我反思报告',
                'command': 'python -c "from infrastructure.self_reflection import self_reflection; report = self_reflection.generate_weekly_report(); print(f\'健康得分: {report[\"summary\"][\"health_score\"]:.1f}\')"',
                'description': '生成自我反思报告'
            }
        ]
        
        for stage in stages:
            result = self.execute_stage(
                stage['name'],
                stage['command'],
                stage['description']
            )
            
            if not self.evaluate_and_continue(result):
                print("\n❌ 阶段失败，停止执行")
                break
        
        # 生成最终报告
        self.generate_final_report()
    
    def generate_final_report(self):
        """生成最终报告"""
        print("\n" + "="*70)
        print("连续执行计划 - 最终报告")
        print("="*70)
        
        total = len(self.results)
        success = sum(1 for r in self.results if r['success'])
        
        print(f"\n总阶段数: {total}")
        print(f"成功阶段: {success}")
        print(f"成功率: {success/total*100:.1f}%")
        
        print("\n阶段详情:")
        for i, result in enumerate(self.results, 1):
            status = "✅" if result['success'] else "❌"
            print(f"  {status} {i}. {result['stage']}")
        
        if success == total:
            print("\n🎉 所有阶段完成！系统已就绪！")
            print("\n下一步:")
            print("  1. 启动后端: python backend/main.py")
            print("  2. 运行基准测试: python tests/benchmark_federation.py")
            print("  3. 开始实际使用")
        else:
            print(f"\n⚠️ {total-success} 个阶段需要关注")
        
        print("="*70)


if __name__ == "__main__":
    executor = ContinuousExecution()
    executor.run_all_stages()
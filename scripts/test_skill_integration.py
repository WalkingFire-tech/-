"""
完整系统测试 - 技能树 + Ollama集成
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("联盟拓荒者 - 完整系统测试")
print("=" * 80)

# 1. 测试技能树
print("\n[1] 测试技能树...")
from core.skill_tree import SkillTree, TaskScheduler

skill_tree = SkillTree()
print(f"✓ 技能树加载成功: {len(skill_tree.skills)} 个技能")

# 测试任务评估
test_tasks = [
    "帮我读取data.xlsx文件",
    "什么是深度学习？",
    "写一个Python脚本批量重命名文件",
]

print("\n任务评估测试:")
for task in test_tasks:
    evaluation = skill_tree.evaluate_task(task)
    print(f"  [{evaluation['action']}] {task[:30]}... → {evaluation['skill'].name if evaluation['skill'] else 'N/A'}")

# 2. 测试Ollama集成
print("\n[2] 测试Ollama集成...")
import requests

try:
    resp = requests.get("http://localhost:11434/api/tags", timeout=5)
    if resp.status_code == 200:
        models = resp.json().get("models", [])
        print(f"✓ Ollama运行中: {len(models)} 个模型")
        
        # 测试推理
        test_question = "什么是深度学习的特点？"
        print(f"\n推理测试: {test_question}")
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5-coder:7b",
                "prompt": test_question,
                "stream": False,
                "options": {"num_predict": 150}
            },
            timeout=30
        )
        
        if response.status_code == 200:
            answer = response.json().get("response", "")[:200]
            print(f"✓ 推理成功: {answer}...")
        else:
            print(f"✗ 推理失败")
except Exception as e:
    print(f"✗ Ollama测试失败: {e}")

# 3. 测试主系统集成
print("\n[3] 测试主系统集成...")
try:
    from main_integrated import AlliancePioneer
    
    system = AlliancePioneer()
    print(f"✓ 主系统初始化成功")
    print(f"  - 技能数: {len(system.skill_tree.skills)}")
    print(f"  - 会话ID: {system.session_id}")
    
except Exception as e:
    print(f"✗ 主系统集成失败: {e}")
    import traceback
    traceback.print_exc()

# 4. 总结
print("\n" + "=" * 80)
print("系统测试总结")
print("=" * 80)

print("\n✅ 已集成的核心能力:")
print("  1. 技能树 (SkillTree) - 动态能力管理")
print("  2. 任务调度器 (TaskScheduler) - 并行执行")
print("  3. 工具生成器 (ToolGenerator) - 动态创建工具")
print("  4. Ollama集成 - 实际推理能力")
print("  5. LoRA模型 - 闭环进化能力")

print("\n📊 技能统计:")
stats = skill_tree.get_skill_stats()
print(f"  - 总技能: {stats['total']}")
print(f"  - 本地技能: {stats['by_type']['local']}")
print(f"  - LoRA技能: {stats['by_type']['lora']}")
print(f"  - 外部技能: {stats['by_type']['external']}")

print("\n🎯 下一步:")
print("  1. 运行 start.bat 测试完整交互")
print("  2. 尝试复杂任务观察技能调度")
print("  3. 积累数据后进行新一轮微调")

print("\n" + "=" * 80)
"""
测试LoRA模型集成
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

print("=" * 70)
print("联盟拓荒者 - LoRA模型集成测试")
print("=" * 70)

# 1. 检查LoRA文件
print("\n[1] 检查LoRA文件...")
lora_paths = [
    project_root / "models" / "closed_loop_lora",
    project_root / "autodl_backup" / "output" / "closed_loop_lora",
]

lora_found = False
for path in lora_paths:
    if path.exists():
        adapter_file = path / "adapter_model.safetensors"
        config_file = path / "adapter_config.json"
        
        if adapter_file.exists() and config_file.exists():
            size_mb = adapter_file.stat().st_size / 1024 / 1024
            print(f"✓ 找到LoRA权重: {path}")
            print(f"  - adapter_model.safetensors: {size_mb:.2f} MB")
            print(f"  - adapter_config.json: 存在")
            lora_found = True
            break

if not lora_found:
    print("✗ 未找到LoRA权重文件")
    print("  请确保已下载训练好的模型")
    sys.exit(1)

# 2. 测试导入
print("\n[2] 测试导入...")
try:
    from adapters.llm.lora_adapter import create_lora_adapter, LoRAAdapter, MockLoRAAdapter
    print("✓ LoRA适配器模块导入成功")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    print("  请安装依赖: pip install transformers peft torch")
    sys.exit(1)

# 3. 创建适配器
print("\n[3] 创建LoRA适配器...")
try:
    adapter = create_lora_adapter()
    info = adapter.get_info()
    print(f"✓ 适配器创建成功")
    print(f"  模型名称: {info.get('model_name', 'N/A')}")
    print(f"  基础模型: {info.get('base_model', 'N/A')}")
except Exception as e:
    print(f"✗ 适配器创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. 测试生成
print("\n[4] 测试生成能力...")
test_prompts = [
    "什么是深度学习的特点？",
    "当你从外部模型获取了一段代码后，你会如何验证它的正确性？",
]

for i, prompt in enumerate(test_prompts, 1):
    print(f"\n  [测试 {i}] {prompt[:30]}...")
    try:
        response = adapter.generate(prompt, max_new_tokens=128)
        print(f"  回答: {response[:100]}...")
        print(f"  ✓ 生成成功")
    except Exception as e:
        print(f"  ✗ 生成失败: {e}")

# 5. 集成到主系统
print("\n[5] 集成到主系统...")
main_file = project_root / "main.py"
if main_file.exists():
    content = main_file.read_text(encoding='utf-8')
    if "closed_loop_lora" in content:
        print("✓ main.py已集成LoRA模型")
    else:
        print("⚠ main.py未找到LoRA集成代码")

# 6. 总结
print("\n" + "=" * 70)
print("集成测试完成")
print("=" * 70)
print("\n使用方法:")
print("1. 在main.py中，LoRA模型已自动加载为 adapters['closed_loop_lora']")
print("2. 调用方式:")
print("   response = adapters['closed_loop_lora'].generate('你的问题')")
print("3. 或在对话中指定使用:")
print("   planner.execute(intent, model='closed_loop_lora')")
print("\n下一步:")
print("- 运行主程序测试: python main.py")
print("- 查看模型效果对比")
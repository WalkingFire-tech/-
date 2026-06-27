"""
验证LoRA模型集成（不依赖PyTorch）
"""
import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent

print("=" * 70)
print("联盟拓荒者 - LoRA模型集成验证")
print("=" * 70)

# 1. 检查文件结构
print("\n[1] 检查文件结构...")

required_files = {
    "LoRA适配器": project_root / "adapters" / "llm" / "lora_adapter.py",
    "LoRA权重": project_root / "models" / "closed_loop_lora" / "adapter_model.safetensors",
    "LoRA配置": project_root / "models" / "closed_loop_lora" / "adapter_config.json",
    "主程序": project_root / "main.py",
}

all_ok = True
for name, path in required_files.items():
    if path.exists():
        if path.suffix == ".py":
            size = path.stat().st_size / 1024
            print(f"✓ {name}: {path.name} ({size:.1f} KB)")
        elif path.suffix == ".safetensors":
            size = path.stat().st_size / 1024 / 1024
            print(f"✓ {name}: {path.name} ({size:.1f} MB)")
        else:
            print(f"✓ {name}: {path.name}")
    else:
        print(f"✗ {name}: 不存在")
        all_ok = False

# 2. 检查LoRA配置
print("\n[2] 检查LoRA配置...")
config_path = project_root / "models" / "closed_loop_lora" / "adapter_config.json"
if config_path.exists():
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print(f"✓ LoRA配置:")
    print(f"  - rank (r): {config.get('r', 'N/A')}")
    print(f"  - alpha: {config.get('lora_alpha', 'N/A')}")
    print(f"  - dropout: {config.get('lora_dropout', 'N/A')}")
    print(f"  - target_modules: {len(config.get('target_modules', []))} 个")
    print(f"  - peft_type: {config.get('peft_type', 'N/A')}")

# 3. 检查main.py集成
print("\n[3] 检查main.py集成...")
main_path = project_root / "main.py"
if main_path.exists():
    content = main_path.read_text(encoding='utf-8')
    
    checks = [
        ("导入LoRA适配器", "from adapters.llm.lora_adapter import create_lora_adapter"),
        ("加载LoRA模型", 'adapters["closed_loop_lora"] = create_lora_adapter()'),
        ("日志输出", "LoRA微调模型已加载"),
    ]
    
    for name, marker in checks:
        if marker in content:
            print(f"✓ {name}")
        else:
            print(f"✗ {name}")
            all_ok = False

# 4. 检查训练结果
print("\n[4] 检查训练结果...")
results_path = project_root / "models" / "closed_loop_lora" / "all_results.json"
if results_path.exists():
    with open(results_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print(f"✓ 训练结果:")
    print(f"  - epoch: {results.get('epoch', 'N/A')}")
    print(f"  - train_loss: {results.get('train_loss', 'N/A')}")
    print(f"  - eval_loss: {results.get('eval_loss', 'N/A')}")
    print(f"  - train_runtime: {results.get('train_runtime', 'N/A')}")

# 5. 检查训练数据
print("\n[5] 检查训练数据...")
data_paths = [
    project_root / "data" / "sft" / "combined_all_training_data.jsonl",
    project_root / "autodl_backup" / "data" / "sft" / "combined_all_training_data.jsonl",
]

for data_path in data_paths:
    if data_path.exists():
        with open(data_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"✓ 训练数据: {len(lines)} 条样本")
        print(f"  路径: {data_path.relative_to(project_root)}")
        break
else:
    print("⚠ 训练数据文件未找到")

# 6. 总结
print("\n" + "=" * 70)
if all_ok:
    print("✓ LoRA模型集成验证通过")
    print("=" * 70)
    print("\n集成状态:")
    print("  ✓ LoRA适配器已创建 (adapters/llm/lora_adapter.py)")
    print("  ✓ LoRA权重已下载 (models/closed_loop_lora/)")
    print("  ✓ 主程序已集成 (main.py)")
    print("\n使用方法:")
    print("  1. 在GPU环境下运行主程序:")
    print("     python main.py")
    print("  2. LoRA模型会自动加载为 adapters['closed_loop_lora']")
    print("  3. 调用方式:")
    print("     response = adapters['closed_loop_lora'].generate('你的问题')")
    print("\n注意事项:")
    print("  - 需要GPU环境（CUDA支持）")
    print("  - 需要安装: pip install transformers peft torch")
else:
    print("✗ 部分检查未通过，请检查上述错误")
    print("=" * 70)
"""
外脑配置助手 - 快速配置API密钥
"""
import os
from pathlib import Path

print("="*60)
print("外脑配置助手")
print("="*60)
print()

env_file = Path(".env")

print("当前支持的远程模型：")
print()
print("1. OpenAI (GPT-4o-mini)")
print("   - 用途: 通用对话、复杂推理")
print("   - 费用: 约 $0.15/百万tokens")
print("   - 获取: https://platform.openai.com/api-keys")
print()
print("2. DeepSeek (推荐，性价比高)")
print("   - 用途: 代码生成、对话")
print("   - 费用: 约 ¥1/百万tokens")
print("   - 获取: https://platform.deepseek.com/")
print()
print("="*60)
print()

# 读取现有配置
existing_config = {}
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                existing_config[key.strip()] = value.strip()

# 显示当前配置
print("当前配置状态：")
print()
if existing_config:
    for key, value in existing_config.items():
        if value and value != 'sk-your-openai-key-here' and value != 'sk-your-deepseek-key-here':
            print(f"  ✅ {key}: 已配置")
        else:
            print(f"  ⚠️  {key}: 未配置")
else:
    print("  ⚠️  未找到配置")

print()
print("="*60)
print()

# 配置选项
print("请选择操作：")
print()
print("  1. 配置 OpenAI API 密钥")
print("  2. 配置 DeepSeek API 密钥")
print("  3. 配置两者")
print("  4. 查看配置指南")
print("  5. 退出")
print()

choice = input("请输入选项 (1-5): ").strip()

if choice == '1':
    print()
    key = input("请输入 OpenAI API 密钥: ").strip()
    if key:
        existing_config['OPENAI_API_KEY'] = key
        print("✅ OpenAI API 密钥已设置")
    else:
        print("❌ 密钥不能为空")

elif choice == '2':
    print()
    key = input("请输入 DeepSeek API 密钥: ").strip()
    if key:
        existing_config['DEEPSEEK_API_KEY'] = key
        print("✅ DeepSeek API 密钥已设置")
    else:
        print("❌ 密钥不能为空")

elif choice == '3':
    print()
    key1 = input("请输入 OpenAI API 密钥 (没有可跳过): ").strip()
    key2 = input("请输入 DeepSeek API 密钥 (没有可跳过): ").strip()
    
    if key1:
        existing_config['OPENAI_API_KEY'] = key1
        print("✅ OpenAI API 密钥已设置")
    if key2:
        existing_config['DEEPSEEK_API_KEY'] = key2
        print("✅ DeepSeek API 密钥已设置")

elif choice == '4':
    print()
    print("="*60)
    print("配置指南")
    print("="*60)
    print()
    print("OpenAI API:")
    print("  1. 访问 https://platform.openai.com/api-keys")
    print("  2. 登录/注册账号")
    print("  3. 点击 'Create new secret key'")
    print("  4. 复制密钥（以 sk- 开头）")
    print()
    print("DeepSeek API:")
    print("  1. 访问 https://platform.deepseek.com/")
    print("  2. 注册账号")
    print("  3. 获取 API 密钥")
    print("  4. 复制密钥")
    print()
    print("="*60)
    exit(0)

elif choice == '5':
    print("退出配置")
    exit(0)

# 保存配置
if choice in ['1', '2', '3']:
    print()
    print("正在保存配置...")
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write("# 外脑配置\n")
        f.write("# 由配置助手自动生成\n\n")
        
        if 'OPENAI_API_KEY' in existing_config:
            f.write(f"OPENAI_API_KEY={existing_config['OPENAI_API_KEY']}\n")
        
        if 'DEEPSEEK_API_KEY' in existing_config:
            f.write(f"DEEPSEEK_API_KEY={existing_config['DEEPSEEK_API_KEY']}\n")
    
    print(f"✅ 配置已保存到 {env_file}")
    print()
    print("="*60)
    print("下一步")
    print("="*60)
    print()
    print("1. 重启服务:")
    print("   python backend/main.py")
    print()
    print("2. 查看日志确认:")
    print("   应该看到 'Loaded remote GPT' 或 'Loaded DeepSeek Chat'")
    print()
    print("3. 测试外脑:")
    print("   在对话中输入复杂问题，系统会自动使用外脑")
    print()
    print("="*60)
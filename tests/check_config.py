import yaml
with open('config/settings.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
    
models = config.get('models', {}).get('local', {}).get('available', {})
print('配置中的模型:')
for name, cfg in models.items():
    print(f'  {name}: max_tokens={cfg.get("max_tokens", "未设置")}')

print("\n测试配置管理器:")
from infrastructure.config_manager import config as cfg_mgr

# 测试不同的键名格式
test_keys = ['qwen2.5-coder:7b', 'qwen2.5-coder.7b', 'qwen2_5-coder_7b']
for key in test_keys:
    model_cfg = cfg_mgr.get_model_config(key)
    print(f'{key} -> max_tokens={model_cfg.get("max_tokens", "未设置")}')
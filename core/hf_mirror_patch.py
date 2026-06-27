"""
向量检索器镜像配置补丁
在导入sentence_transformers之前强制设置镜像
"""
import os
import sys

# 1. 设置环境变量（必须在导入前）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_CACHE'] = os.path.expanduser('~/.cache/huggingface/hub')
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['HF_HUB_OFFLINE'] = '0'  # 允许在线下载（通过镜像）

# 2. 修改huggingface_hub常量（必须在导入前）
try:
    import huggingface_hub.constants as constants
    # 强制修改URL常量
    constants.HUGGINGFACE_CO_URL_HOME = 'https://hf-mirror.com'
    constants.HUGGINGFACE_CO_URL_TEMPLATE = 'https://hf-mirror.com/{repo_id}/resolve/{revision}/{filename}'
    constants.HUGGINGFACE_CO_URL = 'https://hf-mirror.com'
    
    # 修改endpoint
    if hasattr(constants, 'HF_ENDPOINT'):
        constants.HF_ENDPOINT = 'https://hf-mirror.com'
    
    print("✓ huggingface_hub镜像配置成功")
except Exception as e:
    print(f"⚠ huggingface_hub配置失败: {e}")

# 3. Monkey patch huggingface_hub的下载函数
try:
    import huggingface_hub.file_download as file_download
    
    # 保存原始函数
    original_hf_hub_download = file_download.hf_hub_download
    
    def patched_hf_hub_download(*args, **kwargs):
        # 强制使用镜像endpoint
        if 'endpoint' not in kwargs:
            kwargs['endpoint'] = 'https://hf-mirror.com'
        return original_hf_hub_download(*args, **kwargs)
    
    # 替换函数
    file_download.hf_hub_download = patched_hf_hub_download
    
    print("✓ hf_hub_download补丁成功")
except Exception as e:
    print(f"⚠ hf_hub_download补丁失败: {e}")

print("✓ 向量检索器镜像配置完成")
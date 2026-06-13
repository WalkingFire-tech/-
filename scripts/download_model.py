from modelscope import snapshot_download
import os

# 下载模型到当前目录下的 models 文件夹
model_dir = snapshot_download('qwen/Qwen-1_8B-Chat-GGUF', cache_dir='./models', revision='master')
print(f"模型已下载到: {model_dir}")

# 向量检索器镜像配置修复

## 问题
向量检索器仍在尝试连接 `huggingface.co`，导致超时和重试。

## 根本原因
`sentence_transformers` 和 `huggingface_hub` 在导入时会自动连接官方站点，即使设置了环境变量也可能被忽略。

## 修复方案

### 1. 创建镜像补丁 (`core/hf_mirror_patch.py`)
- 在导入前强制设置环境变量
- 修改 `huggingface_hub.constants` 的URL常量
- Monkey patch `hf_hub_download` 函数

### 2. 修改向量检索器 (`core/vector_retriever.py`)
- 在导入 `sentence_transformers` 前导入镜像补丁
- 再次确保环境变量设置

### 3. 修改后端入口 (`backend/main.py`)
- 在所有导入前设置环境变量
- 导入镜像补丁

### 4. 创建启动脚本 (`start_backend.bat`)
- 设置所有必要的环境变量
- 启动后端服务

## 使用方法

### 方法1: 使用启动脚本（推荐）
```bash
start_backend.bat
```

### 方法2: 手动启动
```bash
# Windows
set HF_ENDPOINT=https://hf-mirror.com
set HUGGINGFACE_HUB_CACHE=%USERPROFILE%\.cache\huggingface\hub
set HF_HUB_DISABLE_TELEMETRY=1
set TRANSFORMERS_VERBOSITY=error
python backend/main.py

# Linux/Mac
export HF_ENDPOINT=https://hf-mirror.com
export HUGGINGFACE_HUB_CACHE=~/.cache/huggingface/hub
export HF_HUB_DISABLE_TELEMETRY=1
export TRANSFORMERS_VERBOSITY=error
python backend/main.py
```

### 方法3: 测试配置
```bash
test_mirror.bat
```

## 验证

### 1. 检查环境变量
```python
import os
print(os.environ.get('HF_ENDPOINT'))
# 应输出: https://hf-mirror.com
```

### 2. 检查huggingface_hub配置
```python
import huggingface_hub.constants as c
print(c.HUGGINGFACE_CO_URL_HOME)
# 应输出: https://hf-mirror.com
```

### 3. 检查日志
启动后端后，日志应显示：
```
✓ huggingface_hub镜像配置成功
✓ hf_hub_download补丁成功
✓ 向量检索器镜像配置完成
使用镜像站点: https://hf-mirror.com
```

### 4. 不应出现的错误
```
❌ Connection to huggingface.co timed out
❌ Max retries exceeded with url: huggingface.co
```

## 已知问题

1. **如果仍出现连接huggingface.co的错误**
   - 原因：可能有其他模块在导入前连接官方站点
   - 解决：重启后端服务，确保使用 `start_backend.bat`

2. **模型已缓存但仍尝试下载**
   - 原因：缓存验证需要连接官方站点
   - 解决：设置 `HF_HUB_OFFLINE=1`（严格离线模式）

3. **镜像站点速度慢**
   - 原因：镜像站点带宽有限
   - 解决：使用已缓存的模型，或等待下载完成

## 严格离线模式

如果不需要下载新模型，可以启用严格离线模式：

```bash
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set HF_DATASETS_OFFLINE=1
```

这样将只使用本地缓存，不尝试任何网络连接。

## 相关文件

- `core/hf_mirror_patch.py` - 镜像补丁
- `core/vector_retriever.py` - 向量检索器
- `backend/main.py` - 后端入口
- `start_backend.bat` - 启动脚本
- `test_mirror.bat` - 测试脚本
- `test_mirror_config.py` - 配置测试

## 版本
- v3.1.3 - 修复刷新按钮
- v3.1.4 - 修复镜像配置（当前）
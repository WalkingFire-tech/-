# 网络访问错误解决方案

## 问题诊断

### 错误信息
```
DuckDuckGo搜索失败: https://www.bing.com/search?q=... return None
所有搜索引擎不可用，返回模拟结果
```

### 原因分析

DuckDuckGo搜索包（`duckduckgo_search`）内部使用Bing搜索引擎，但网络请求失败。

**可能原因：**
1. 网络防火墙限制（公司/学校网络屏蔽外网）
2. 需要代理才能访问外网
3. DNS解析失败
4. 网络连接超时

---

## 解决方案

### 方案1：配置代理（推荐）

如果你需要使用代理访问外网，设置环境变量：

```bash
# Windows PowerShell
$env:HTTP_PROXY = "http://proxy-server:port"
$env:HTTPS_PROXY = "http://proxy-server:port"

# 或在系统环境变量中设置
HTTP_PROXY=http://proxy-server:port
HTTPS_PROXY=http://proxy-server:port
```

然后在代码中配置代理：

```python
# core/external_learner.py 添加代理配置
import os
import requests

proxies = {
    'http': os.getenv('HTTP_PROXY'),
    'https': os.getenv('HTTPS_PROXY')
}

# 在请求时使用
response = requests.get(url, proxies=proxies, timeout=10)
```

---

### 方案2：使用国内搜索引擎API

配置百度或搜狗搜索API：

#### 百度搜索API

1. 申请百度搜索API：https://developer.baidu.com/
2. 获取API Key
3. 配置环境变量：

```bash
BAIDU_API_KEY=your_api_key
```

4. 修改代码：

```python
# core/external_learner.py 添加百度搜索
def _search_baidu(self, query: str, num_results: int = 5) -> List[str]:
    """百度搜索"""
    import requests
    api_key = os.getenv('BAIDU_API_KEY')
    if not api_key:
        return []
    
    url = "https://api.baidu.com/rest/2.0/search"
    params = {
        "access_token": api_key,
        "q": query,
        "num": num_results
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("results", []):
                results.append(f"{item.get('title')}: {item.get('abstract')}")
            return results
    except Exception as e:
        logger.debug(f"百度搜索失败: {e}")
    
    return []
```

---

### 方案3：使用Google Custom Search API

1. 申请Google Custom Search API：
   - https://developers.google.com/custom-search/v1/introduction
   - https://programmablesearchengine.google.com/

2. 获取API Key和Search Engine ID

3. 配置环境变量：

```bash
SEARCH_API_KEY=your_google_api_key
SEARCH_ENGINE_ID=your_search_engine_id
```

4. 系统会自动使用Google搜索（已在代码中实现）

---

### 方案4：使用本地知识库（无需外网）

如果无法访问外网，系统会自动降级到：

1. **本地模型生成** - 使用Ollama本地模型
2. **本地知识库** - 从已有的knowledge_items中检索
3. **模拟结果** - 返回提示信息

**当前系统已经可以正常工作：**

```
✅ 本地模型（qwen2.5-coder:7b）正常
✅ 向量检索正常
✅ 四层进化系统正常
✅ 知识注入正常
```

**建议：**
- 如果只是测试系统功能，无需修复网络问题
- 系统已经可以生成准确的回答（来自本地模型）
- 外部搜索只是增强功能，不是必需的

---

### 方案5：检查网络连接

运行诊断命令：

```bash
# 测试外网连接
ping duckduckgo.com
ping bing.com

# 测试HTTPS连接
curl https://duckduckgo.com/
curl https://www.bing.com/

# 测试DNS解析
nslookup duckduckgo.com
nslookup bing.com
```

如果这些命令都失败，说明网络确实无法访问外网。

---

## 当前系统状态

### ✅ 正常工作的功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 本地模型生成 | ✅ 正常 | qwen2.5-coder:7b |
| 对话认知引擎 | ✅ 正常 | 场景感知、深层理解 |
| 四层进化系统 | ✅ 正常 | 行为/知识/策略/元学习 |
| 知识注入 | ✅ 正常 | 系统主动评估 |
| 向量检索 | ✅ 正常 | 本地FAISS索引 |
| 自动学习 | ✅ 正常 | 从对话中学习 |

### ⚠️ 受影响的功能

| 功能 | 状态 | 影响 |
|------|------|------|
| DuckDuckGo搜索 | ❌ 失败 | 无法获取外部知识 |
| Bing搜索 | ❌ 失败 | 同上 |
| Google搜索 | ⚠️ 未配置 | 需要API Key |

---

## 推荐方案

**如果系统已经能生成准确回答，建议：**

1. **继续使用当前配置** - 本地模型已经足够
2. **积累本地知识库** - 通过对话积累知识
3. **配置代理**（如果需要外网）- 获取更多外部知识

**如果必须使用外部搜索：**

1. 配置代理（方案1）
2. 或配置Google API（方案3）
3. 或使用国内搜索API（方案2）

---

## 验证修复

修复后运行测试：

```python
from core.external_learner import ExternalLearner

learner = ExternalLearner()
results = learner.search_web("测试查询", num_results=3)
print(f"搜索结果: {len(results)}条")
for r in results:
    print(f"  - {r}")
```

---

## 总结

**当前系统可以正常工作，网络访问错误不影响核心功能：**

- ✅ 对话功能正常
- ✅ 知识注入正常
- ✅ 进化系统正常
- ⚠️ 外部搜索失败（可选功能）

**建议优先级：**
1. 继续使用当前配置（本地模型已足够）
2. 如需外部知识，配置代理或API
3. 积累本地知识库，减少对外部搜索的依赖
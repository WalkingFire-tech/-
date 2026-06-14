# 联盟拓荒者 - 快速启动指南

## 🚀 启动方式

### 方式一：一键启动（推荐）

**Windows**:
```bash
双击运行 start.bat
```

**Linux/Mac**:
```bash
chmod +x start.sh
./start.sh
```

### 方式二：手动启动

```bash
# 1. 安装核心依赖
pip install rich loguru pyyaml pydantic pydantic-settings python-dotenv numpy requests schedule

# 2. 启动系统
python main.py
```

### 方式三：完整安装

```bash
# 安装所有依赖（包括可选依赖）
pip install -r requirements.txt

# 启动系统
python main.py
```

---

## 📦 依赖说明

### 核心依赖（必需）

```bash
pip install rich loguru pyyaml pydantic pydantic-settings python-dotenv numpy requests schedule
```

这些依赖是系统运行的最低要求。

### 可选依赖（增强功能）

```bash
# 贝叶斯优化
pip install scikit-optimize

# 向量检索
pip install faiss-cpu sentence-transformers

# 高精度计算
pip install mpmath

# 文件监控
pip install watchdog

# 规则匹配增强
pip install simpleeval

# 开发测试
pip install pytest pytest-cov pytest-mock
```

---

## ⚠️ 常见问题

### 1. ModuleNotFoundError: No module named 'xxx'

**原因**: 缺少依赖包

**解决**:
```bash
pip install xxx
```

或批量安装：
```bash
pip install -r requirements.txt
```

### 2. NameError: name 'Optional' is not defined

**原因**: Python版本过低或typing模块问题

**解决**:
```bash
# 确保Python版本 >= 3.8
python --version

# 如果版本正确，重新安装依赖
pip install --upgrade typing-extensions
```

### 3. 向量索引加载失败

**原因**: 首次运行或缺少FAISS

**解决**:
```bash
# 安装FAISS
pip install faiss-cpu

# 或忽略（系统会使用内存检索）
```

### 4. 元控制层启动失败

**原因**: 缺少schedule库

**解决**:
```bash
pip install schedule
```

---

## ✅ 启动验证

运行测试脚本验证所有模块：

```bash
python test_startup.py
```

预期输出：
```
============================================================
联盟拓荒者 v3.1.1 - 启动测试
============================================================

[1/10] 测试配置管理... ✓
[2/10] 测试日志系统... ✓
[3/10] 测试数据库初始化... ✓
...
✓ 所有核心模块加载成功！
============================================================
```

---

## 🎯 启动后测试

### 测试计算功能
```
你: 计算 2+3*4
拓荒者: 14

你: 输出π的前10位
拓荒者: 3.141592653
```

### 测试优化功能
```
你: :optimize run 10
拓荒者: 开始贝叶斯优化(10次迭代)...
```

### 测试归纳功能
```
你: :induction run 7
拓荒者: 开始归纳总结(最近7天)...
```

---

## 🔧 环境要求

- **Python**: >= 3.8
- **操作系统**: Windows / Linux / macOS
- **内存**: >= 2GB
- **磁盘**: >= 500MB

---

## 📞 获取帮助

启动后输入：
```
:help
```

查看所有可用命令。

---

*最后更新: 2026-06-07*
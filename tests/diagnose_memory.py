"""
内存诊断和优化建议
"""
import sys
import psutil
import subprocess
from pathlib import Path

print("="*60)
print("内存诊断报告")
print("="*60)

# 系统内存
mem = psutil.virtual_memory()
print(f"\n📊 系统内存状态:")
print(f"  总内存: {mem.total / (1024**3):.2f} GB")
print(f"  可用内存: {mem.available / (1024**3):.2f} GB")
print(f"  已使用: {mem.used / (1024**3):.2f} GB")
print(f"  使用率: {mem.percent}%")

# Python进程
print(f"\n🐍 Python进程:")
python_procs = []
for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
    if proc.info['name'] == 'python.exe':
        mem_mb = proc.info['memory_info'].rss / (1024**2)
        python_procs.append((proc.info['pid'], mem_mb))
        print(f"  PID {proc.info['pid']}: {mem_mb:.1f} MB")

total_python_mem = sum(m for _, m in python_procs)
print(f"  总计: {total_python_mem:.1f} MB ({total_python_mem/1024:.2f} GB)")

# 分析问题
print(f"\n🔍 问题分析:")

if mem.percent > 80:
    print(f"  ⚠️  系统内存使用率过高 ({mem.percent}%)")
else:
    print(f"  ✅ 系统内存充足 ({mem.percent}%)")

if total_python_mem > 2000:
    print(f"  ⚠️  Python进程占用过多内存 ({total_python_mem:.0f} MB)")
    print(f"     可能原因:")
    print(f"     - 加载了多个大模型")
    print(f"     - FAISS向量索引过大")
    print(f"     - 后台线程过多")
else:
    print(f"  ✅ Python内存占用正常 ({total_python_mem:.0f} MB)")

# 检查Ollama
print(f"\n🦙 Ollama状态:")
try:
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        models = result.stdout.strip().split('\n')
        print(f"  已加载模型: {len(models)-1} 个")
        for model in models[1:6]:  # 只显示前5个
            if model.strip():
                print(f"    - {model.strip()[:50]}")
    else:
        print(f"  ⚠️  Ollama未运行")
except:
    print(f"  ⚠️  Ollama未安装或未运行")

# 优化建议
print(f"\n💡 优化建议:")

suggestions = []

if total_python_mem > 2000:
    suggestions.append("1. 使用轻量级服务: python backend_lite.py")
    suggestions.append("2. 减少加载的模型数量")
    suggestions.append("3. 禁用FAISS向量索引")

if mem.percent > 80:
    suggestions.append("4. 关闭不必要的应用")
    suggestions.append("5. 增加虚拟内存")

# 检查FAISS
faiss_path = Path("data/faiss_index")
if faiss_path.exists():
    faiss_size = sum(f.stat().st_size for f in faiss_path.glob("*") if f.is_file())
    faiss_mb = faiss_size / (1024**2)
    print(f"\n📚 FAISS索引:")
    print(f"  大小: {faiss_mb:.1f} MB")
    if faiss_mb > 500:
        suggestions.append("6. 清理FAISS索引或禁用向量检索")

if suggestions:
    print()
    for s in suggestions:
        print(f"  {s}")
else:
    print(f"  ✅ 系统配置良好，无需优化")

# 推荐启动方式
print(f"\n🚀 推荐启动方式:")

if total_python_mem < 1500 and mem.percent < 70:
    print(f"  完整服务: python backend/main.py")
    print(f"  或使用: start.bat")
else:
    print(f"  轻量服务: python backend_lite.py ⭐推荐")
    print(f"  特点: 只加载必要组件，减少内存占用")

print(f"\n" + "="*60)
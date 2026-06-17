"""
测试异步文件夹学习功能
"""
import requests
import time

BASE_URL = "http://localhost:8000"

print("\n" + "="*60)
print("📁 测试异步文件夹学习")
print("="*60)

# 测试文件夹（使用当前项目）
test_folder = "C:/Users/Administrator/alliance_pioneer/core"

print(f"\n测试文件夹: {test_folder}")

# 1. 启动异步学习
print("\n【步骤1】启动异步学习...")
try:
    response = requests.post(
        f"{BASE_URL}/api/folder/learn_async",
        json={"path": test_folder},
        timeout=10
    )
    
    result = response.json()
    
    if result.get("success"):
        task_id = result.get("task_id")
        print(f"✅ 任务已创建: {task_id}")
    else:
        print(f"❌ 启动失败: {result.get('error')}")
        exit(1)
        
except Exception as e:
    print(f"❌ 请求失败: {e}")
    exit(1)

# 2. 轮询进度
print("\n【步骤2】轮询进度...")
max_wait = 60  # 最多等待60秒
start_time = time.time()

while time.time() - start_time < max_wait:
    try:
        response = requests.get(
            f"{BASE_URL}/api/folder/learn_status/{task_id}",
            timeout=5
        )
        
        status = response.json()
        
        if status.get("success"):
            progress = status.get("progress", 0)
            message = status.get("message", "")
            current_file = status.get("current_file", "")
            
            print(f"  进度: {progress}% - {message}")
            if current_file:
                print(f"  当前: {current_file}")
            
            # 检查是否完成
            task_status = status.get("status")
            if task_status == "completed":
                print("\n✅ 学习完成！")
                print(f"  总文件: {status.get('total_files', 0)}")
                print(f"  已处理: {status.get('processed', 0)}")
                print(f"  知识条数: {status.get('knowledge', 0)}")
                print(f"  生成规则: {status.get('rules', 0)}")
                print(f"  生成工具: {status.get('tools', 0)}")
                break
            elif task_status == "failed":
                print(f"\n❌ 学习失败: {message}")
                break
        
        time.sleep(2)
        
    except Exception as e:
        print(f"  ⚠️ 查询失败: {e}")
        time.sleep(2)

# 3. 查看所有任务
print("\n【步骤3】查看所有任务...")
try:
    response = requests.get(
        f"{BASE_URL}/api/folder/learn_tasks",
        timeout=5
    )
    
    result = response.json()
    tasks = result.get("tasks", [])
    
    print(f"\n最近任务: {len(tasks)}个")
    for task in tasks:
        print(f"  - {task.get('task_id')[:8]}... : {task.get('status')} - {task.get('message')}")
        
except Exception as e:
    print(f"❌ 查询失败: {e}")

print("\n" + "="*60)
print("✅ 测试完成")
print("="*60)
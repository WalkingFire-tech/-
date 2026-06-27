import paramiko
import os
from scp import SCPClient

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("连接AutoDL...")
    ssh.connect('connect.westd.seetacloud.com', port=53993, username='root', password='SuQo8fqg1agE', timeout=30)
    print("连接成功")
    
    # 本地保存路径
    local_dir = r"C:\Users\Administrator\alliance_pioneer\models\closed_loop_lora"
    os.makedirs(local_dir, exist_ok=True)
    
    # 使用SCP下载文件
    with SCPClient(ssh.get_transport()) as scp:
        # 下载关键文件
        files = [
            'adapter_config.json',
            'adapter_model.safetensors',
            'trainer_state.json',
            'all_results.json'
        ]
        
        remote_dir = '/root/autodl-tmp/alliance_pioneer/output/closed_loop_lora/'
        
        for file in files:
            remote_path = remote_dir + file
            local_path = os.path.join(local_dir, file)
            print(f"下载 {file}...")
            try:
                scp.get(remote_path, local_path)
                print(f"  ✓ {file} 已下载")
            except Exception as e:
                print(f"  ✗ {file} 下载失败: {e}")
    
    print(f"\n✓ LoRA模型已保存到: {local_dir}")
    
    # 列出下载的文件
    print("\n已下载文件:")
    for f in os.listdir(local_dir):
        size = os.path.getsize(os.path.join(local_dir, f))
        print(f"  {f}: {size/1024/1024:.2f} MB")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
finally:
    ssh.close()
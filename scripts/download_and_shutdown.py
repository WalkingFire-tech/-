import paramiko
import os
import tarfile
from io import BytesIO
from scp import SCPClient

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("连接AutoDL...")
    ssh.connect('connect.westd.seetacloud.com', port=53993, username='root', password='SuQo8fqg1agE', timeout=30)
    print("连接成功")
    
    # 1. 打包所有重要文件
    print("\n=== 打包文件 ===")
    pack_cmd = '''
    cd /root/autodl-tmp/alliance_pioneer
    tar -czf /root/autodl-tmp/alliance_pioneer_backup.tar.gz \
        output/closed_loop_lora/adapter_config.json \
        output/closed_loop_lora/adapter_model.safetensors \
        output/closed_loop_lora/trainer_state.json \
        output/closed_loop_lora/all_results.json \
        output/closed_loop_lora/trainer_log.jsonl \
        data/sft/combined_all_training_data.jsonl \
        config/train_closed_loop_lora.yaml
    ls -lh /root/autodl-tmp/alliance_pioneer_backup.tar.gz
    '''
    stdin, stdout, stderr = ssh.exec_command(pack_cmd)
    print(stdout.read().decode('utf-8'))
    
    # 2. 下载打包文件
    print("\n=== 下载文件到本地 ===")
    local_dir = r"C:\Users\Administrator\alliance_pioneer\backups"
    os.makedirs(local_dir, exist_ok=True)
    
    local_file = os.path.join(local_dir, "alliance_pioneer_backup.tar.gz")
    
    with SCPClient(ssh.get_transport()) as scp:
        scp.get('/root/autodl-tmp/alliance_pioneer_backup.tar.gz', local_file)
    
    size = os.path.getsize(local_file) / 1024 / 1024
    print(f"✓ 备份文件已下载: {local_file}")
    print(f"  大小: {size:.2f} MB")
    
    # 3. 解压到本地
    print("\n=== 解压文件 ===")
    extract_dir = r"C:\Users\Administrator\alliance_pioneer\autodl_backup"
    os.makedirs(extract_dir, exist_ok=True)
    
    with tarfile.open(local_file, 'r:gz') as tar:
        tar.extractall(extract_dir)
    
    print(f"✓ 文件已解压到: {extract_dir}")
    
    # 列出解压的文件
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            path = os.path.join(root, file)
            size = os.path.getsize(path) / 1024 / 1024
            rel_path = os.path.relpath(path, extract_dir)
            print(f"  {rel_path}: {size:.2f} MB")
    
    # 4. 关闭AutoDL实例
    print("\n=== 关闭AutoDL实例 ===")
    print("注意: 请在AutoDL控制台手动关机以停止计费")
    print("控制台地址: https://www.autodl.com/console/instance/list")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
finally:
    ssh.close()
    print("\n连接已关闭")
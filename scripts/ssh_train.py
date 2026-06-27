import paramiko
import time
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("连接AutoDL...")
    ssh.connect('connect.westd.seetacloud.com', port=53993, username='root', password='SuQo8fqg1agE', timeout=30)
    print("连接成功")
    
    # 启动训练（使用已下载的本地模型）
    cmd = 'source /root/miniconda3/etc/profile.d/conda.sh && conda activate base && cd /root/autodl-tmp/alliance_pioneer && llamafactory-cli train config/train_closed_loop_lora.yaml'
    
    print(f"执行命令: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    
    # 实时读取输出
    print("\n=== 训练输出 ===")
    start_time = time.time()
    while time.time() - start_time < 1800:  # 30分钟超时
        if stdout.channel.recv_ready():
            line = stdout.channel.recv(1024).decode('utf-8', errors='ignore')
            print(line, end='')
            sys.stdout.flush()
        if stdout.channel.exit_status_ready():
            break
        time.sleep(0.1)
    
    print("\n=== 训练结束 ===")
    
except Exception as e:
    print(f"错误: {e}")
finally:
    ssh.close()
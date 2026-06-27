import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("连接AutoDL...")
    ssh.connect('connect.westd.seetacloud.com', port=53993, username='root', password='SuQo8fqg1agE', timeout=30)
    print("连接成功")
    
    # 检查输出目录
    cmd = 'ls -lh /root/autodl-tmp/alliance_pioneer/output/closed_loop_lora/'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print("\n=== LoRA模型文件 ===")
    print(stdout.read().decode('utf-8'))
    
    # 读取adapter_config.json
    cmd = 'cat /root/autodl-tmp/alliance_pioneer/output/closed_loop_lora/adapter_config.json'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print("\n=== adapter_config.json ===")
    print(stdout.read().decode('utf-8'))
    
    # 检查文件大小
    cmd = 'du -sh /root/autodl-tmp/alliance_pioneer/output/closed_loop_lora/'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print("\n=== 总大小 ===")
    print(stdout.read().decode('utf-8'))
    
except Exception as e:
    print(f"错误: {e}")
finally:
    ssh.close()
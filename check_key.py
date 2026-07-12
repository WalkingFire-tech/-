from infrastructure.config_manager import config
k = config.get("deepseek_api_key", "")
with open("tmp_key_check.txt", "w") as f:
    f.write(f"key_len={len(k)}\n")
    f.write(f"has_key={bool(k)}\n")
    if k:
        f.write(f"prefix={k[:4]}\n")
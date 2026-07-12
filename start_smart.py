import subprocess
import sys
import time
import os
import signal
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

CWD = r"C:\Users\Administrator\alliance_pioneer"
WATCH_DIRS = ["backend", "core", "infrastructure", "config"]
PORT = 8000

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

def _setup_cmd_logger():
    log_dir = os.path.join(CWD, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "cmd_output.log")
    handler = TimedRotatingFileHandler(
        log_file, when="midnight", interval=1, backupCount=7, encoding="utf-8"
    )
    handler.suffix = "%Y-%m-%dd"
    handler.extMatch = r"^\d{4}-\d{2}-\d{2}d$"
    fmt = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(fmt)
    cmd_logger = logging.getLogger("pioneer_cmd")
    cmd_logger.setLevel(logging.INFO)
    cmd_logger.addHandler(handler)
    return cmd_logger, log_file

def clear_pycache():
    for root, dirs, files in os.walk(CWD):
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            try:
                import shutil
                shutil.rmtree(pycache_path, ignore_errors=True)
            except Exception:
                logger.warning("操作降级跳过")

def kill_port():
    try:
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for line in result.stdout.splitlines():
            if f":{PORT}" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5,
                               creationflags=subprocess.CREATE_NO_WINDOW)
                print(f"  Killed PID {pid}")
    except Exception as e:
        print(f"  Warning: {e}")

def wait_port_free(timeout=10):
    for i in range(timeout):
        try:
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            listening = any(f":{PORT}" in l and "LISTENING" in l for l in result.stdout.splitlines())
            if not listening:
                return True
        except Exception:
            logger.warning("操作降级跳过")
        time.sleep(1)
    return False

def start_server(log_file=None):
    clear_pycache()
    kill_port()
    wait_port_free()
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    if log_file:
        log_out = open(log_file, "a", encoding="utf-8")
        log_out.write(f"\n{'='*60}\n[{datetime.now().isoformat()}] Server starting...\n{'='*60}\n")
        log_out.flush()
    else:
        log_out = None
    
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main_fast:app",
         "--host", "0.0.0.0", "--port", str(PORT),
         "--timeout-keep-alive", "30"],
        cwd=CWD,
        env=env,
        stdout=log_out if log_out else subprocess.PIPE,
        stderr=subprocess.STDOUT if log_out else subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return proc, log_out

def main():
    cmd_logger, log_path = _setup_cmd_logger()
    
    print("=" * 50)
    print("  Alliance Pioneer - Smart Starter")
    print("=" * 50)
    print(f"  CMD log: {log_path}")
    print()
    
    proc, log_out = start_server(log_path)
    cmd_logger.info(f"Server started (PID: {proc.pid})")
    print(f"  Server started (PID: {proc.pid})")
    print(f"  URL:  http://localhost:{PORT}/")
    print(f"  Docs: http://localhost:{PORT}/docs")
    print()
    print("  Watching for file changes...")
    print()
    
    try:
        from watchfiles import watch
        watch_paths = [os.path.join(CWD, d) for d in WATCH_DIRS]
        
        for changes in watch(*watch_paths):
            changed_files = [os.path.basename(c[1]) for c in changes]
            msg = f"Change detected: {', '.join(changed_files)}"
            cmd_logger.info(msg)
            print(f"\n  [{msg}]")
            print("  Restarting server...")
            
            if log_out:
                log_out.write(f"\n[{datetime.now().isoformat()}] Restarting due to: {msg}\n")
                log_out.flush()
            
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            
            if log_out:
                log_out.close()
            
            proc, log_out = start_server(log_path)
            cmd_logger.info(f"Server restarted (PID: {proc.pid})")
            print(f"  Server restarted (PID: {proc.pid})")
            
    except ImportError:
        print("  watchfiles not available, running without auto-reload")
        proc.wait()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        cmd_logger.info("Server shutdown by user")
        proc.terminate()
        proc.wait()
    finally:
        if log_out:
            log_out.close()

if __name__ == "__main__":
    main()
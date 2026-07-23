import re

_DANGEROUS_PATTERNS = [
    r'\brm\s+-rf\b', r'\bdel\s+/s\b', r'\bformat\b', r'\bfdisk\b',
    r'\bmkfs\b', r'\bshutdown\b', r'\breboot\b', r'\btaskkill\b',
    r'\breg\s+delete\b', r'\breg\s+add\b', r'\bnet\s+user\b',
    r'\bcipher\b', r'\bsfc\b', r'\bdism\b', r'\bbcdedit\b',
    r'\bos\.remove\b', r'\bshutil\.rmtree\b', r'\bos\.system\b',
]

_PIP_PACKAGE_MAP = {
    "cv2": "opencv-python", "PIL": "Pillow", "sklearn": "scikit-learn",
    "serial": "pyserial", "usb": "pyusb", "yaml": "pyyaml",
    "dotenv": "python-dotenv", "bs4": "beautifulsoup4",
    "folium": "folium", "serial.tools": "pyserial",
    "winreg": None,
}

_INSTALLED_IN_SESSION: set = set()

_MAX_ATTEMPTS = 3
_EXECUTION_TIMEOUT = 30

_SHELL_KEYWORDS = {
    "cmd", "powershell", "shell", "bash", "ping", "ipconfig", "netstat",
    "tasklist", "systeminfo", "dir", "ls", "cat", "grep", "python",
    "node", "npm", "docker", "git", "curl", "wget", "hostname",
    "whoami", "echo", "type", "find", "sc ", "net ", "wmic",
    "get-", "set-", "remove-", "new-",
}

_PS_ERROR_PATTERNS = [
    "不是内部或外部命令", "不是可运行的程序", "CommandNotFoundException",
    "FullyQualifiedErrorId", "CategoryInfo", "无法将",
    "项识别为", "ParameterBindingException", "ParseException",
]
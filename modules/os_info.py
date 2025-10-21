# system_info/os_info.py
import platform
from datetime import datetime

def get_os_info():
    """Return basic OS info (name, version, architecture)."""
    return {
        "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "OS Name": platform.system(),
        "Version": platform.version(),
        "Architecture": platform.machine()
    }
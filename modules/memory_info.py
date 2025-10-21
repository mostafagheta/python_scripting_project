# system_info/memory_info.py
import psutil
import subprocess
import shlex
import re

def get_memory_info():
    """Return memory total, type, frequency, and channel configuration."""
    info = {"Total (GB)": None, "Type": None, "Frequency": None, "Channel": None}
    try:
        vm = psutil.virtual_memory()
        info["Total (GB)"] = round(vm.total / (1024 ** 3), 2)
    except:
        pass

    try:
        out = subprocess.check_output(["dmidecode", "-t", "17"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Type:") and "DDR" in line:
                info["Type"] = line.split(":", 1)[1].strip()
            elif line.startswith("Speed:") and "Unknown" not in line:
                info["Frequency"] = line.split(":", 1)[1].strip()
            elif line.startswith("Rank:") or line.startswith("Channel:"):
                info["Channel"] = line.split(":", 1)[1].strip()
    except:
        pass

    # fallback to lshw (may not be installed) for non-root friendly info
    if not info.get("Type") or not info.get("Frequency"):
        try:
            out = subprocess.check_output(shlex.split("lshw -class memory -short"), text=True, stderr=subprocess.DEVNULL, timeout=3)
            # sample lines may contain 'DIMM' with size and description
            for line in out.splitlines():
                line = line.strip()
                if 'DIMM' in line or 'bank' in line.lower():
                    # try to extract DDR and speed
                    mtype = re.search(r'(DDR[0-9]+)', line, re.IGNORECASE)
                    if mtype and not info.get('Type'):
                        info['Type'] = mtype.group(1).upper()
                    mspeed = re.search(r'([0-9]+)MHz', line, re.IGNORECASE)
                    if mspeed and not info.get('Frequency'):
                        info['Frequency'] = mspeed.group(1) + ' MHz'
        except Exception:
            pass

    return info
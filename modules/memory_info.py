# system_info/memory_info.py
import psutil
import subprocess
import shlex
import re
import shutil
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
        dmidecode_path = shutil.which('dmidecode')
        dmidecode_failed = False
        if dmidecode_path:
            try:
                out = subprocess.check_output(["dmidecode", "-t", "17"], text=True, stderr=subprocess.STDOUT, timeout=4)
            except Exception:
                out = ''
                dmidecode_failed = True
        else:
            out = ''
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
    lshw_path = shutil.which('lshw')
    if not info.get("Type") or not info.get("Frequency"):
        if lshw_path:
            try:
                out = subprocess.check_output(shlex.split("lshw -class memory -short"), text=True, stderr=subprocess.DEVNULL, timeout=3)
                for line in out.splitlines():
                    line = line.strip()
                    if 'DIMM' in line or 'bank' in line.lower():
                        mtype = re.search(r'(DDR[0-9]+)', line, re.IGNORECASE)
                        if mtype and not info.get('Type'):
                            info['Type'] = mtype.group(1).upper()
                        mspeed = re.search(r'([0-9]+)MHz', line, re.IGNORECASE)
                        if mspeed and not info.get('Frequency'):
                            info['Frequency'] = mspeed.group(1) + ' MHz'
            except Exception:
                pass

    # Provide helpful messages if values remain missing
    if not info.get('Type'):
        if dmidecode_path is None and lshw_path is None:
            info['Type'] = 'Unavailable (install dmidecode or lshw)'
        elif dmidecode_path and dmidecode_failed:
            info['Type'] = 'Requires sudo to read dmidecode'
        else:
            info['Type'] = None

    if not info.get('Frequency'):
        if dmidecode_path is None and lshw_path is None:
            info['Frequency'] = 'Unavailable (install dmidecode or lshw)'
        elif dmidecode_path and dmidecode_failed:
            info['Frequency'] = 'Requires sudo to read dmidecode'
        else:
            info['Frequency'] = None

    return info
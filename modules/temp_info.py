"""
temperature_info.py
-------------------
Module to collect temperature readings for CPU, GPU, RAM, and VRM.
Handles Linux and Windows gracefully. Returns structured dictionary.
"""

import platform
import psutil
import subprocess
import os
import glob
import re
from . import gpu_info as _gpu_info

def get_temperatures():
    temps = {
        "CPU Temperature (°C)": None,
        "GPU Temperature (°C)": None,
        "RAM Temperature (°C)": None,
        "VRM Temperature (°C)": None
    }

    try:
        system = platform.system().lower()

        # --- Linux implementation ---
        if system == "linux":
            try:
                sensors = psutil.sensors_temperatures()
                # CPU
                if "coretemp" in sensors:
                    cpu_temps = [t.current for t in sensors["coretemp"] if t.current is not None]
                    if cpu_temps:
                        temps["CPU Temperature (°C)"] = round(sum(cpu_temps) / len(cpu_temps), 1)
            except Exception:
                pass

            # GPU (prefer nvidia-smi; fallback to gpu_info which may read hwmon)
            got_gpu = False
            try:
                gpu_temp = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                ).decode().strip()
                if gpu_temp:
                    temps["GPU Temperature (°C)"] = float(gpu_temp)
                    got_gpu = True
            except Exception:
                got_gpu = False

            if not got_gpu:
                try:
                    g = _gpu_info.get_gpu_info()
                    gt = g.get('Temperature')
                    if gt:
                        # gt may be like '60.0 °C'
                        m = re.search(r"([0-9]+\.?[0-9]*)", str(gt))
                        if m:
                            temps["GPU Temperature (°C)"] = float(m.group(1))
                except Exception:
                    pass

            # try scanning /sys/class/hwmon for additional sensors (GPU, VRM, RAM)
            try:
                for hw in glob.glob('/sys/class/hwmon/hwmon*'):
                    # read 'name' if available to hint mapping
                    name_file = os.path.join(hw, 'name')
                    name = None
                    if os.path.exists(name_file):
                        try:
                            name = open(name_file, 'r').read().strip().lower()
                        except Exception:
                            name = None

                    # read temp inputs
                    for tfile in glob.glob(os.path.join(hw, 'temp*_input')):
                        try:
                            val = open(tfile, 'r').read().strip()
                            if not val:
                                continue
                            t = float(val)
                            if t > 1000:
                                t = t / 1000.0
                            t = round(t, 1)
                        except Exception:
                            continue

                        # decide where to assign this temp
                        label_file = tfile.replace('_input', '_label')
                        label = None
                        if os.path.exists(label_file):
                            try:
                                label = open(label_file, 'r').read().strip().lower()
                            except Exception:
                                label = None

                            target = None
                            if name and 'gpu' in name:
                                target = 'GPU Temperature (°C)'
                            elif label and ('gpu' in label or 'core' in label and 'gpu' in label):
                                target = 'GPU Temperature (°C)'
                            elif label and ('cpu' in label or 'package' in label or 'core' in label):
                                target = 'CPU Temperature (°C)'
                            elif re.search(r'vrm|vreg|vrm|vcore', label or '' , re.IGNORECASE) or re.search(r'vrm|vreg|vrm|vcore', name or '' , re.IGNORECASE):
                                target = 'VRM Temperature (°C)'
                            elif re.search(r'dram|mem|ram|memory', label or '' , re.IGNORECASE) or re.search(r'dram|mem|ram|memory', name or '' , re.IGNORECASE):
                                target = 'RAM Temperature (°C)'

                        if target and temps.get(target) is None:
                            temps[target] = t
            except Exception:
                pass

        # --- Windows implementation ---
        elif system == "windows":
            try:
                import wmi
                w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                sensors = w.Sensor()
                for sensor in sensors:
                    if sensor.SensorType == u'Temperature':
                        name = sensor.Name.lower()
                        if "cpu" in name:
                            temps["CPU Temperature (°C)"] = sensor.Value
                        elif "gpu" in name:
                            temps["GPU Temperature (°C)"] = sensor.Value
                        elif "ram" in name:
                            temps["RAM Temperature (°C)"] = sensor.Value
                        elif "vrm" in name:
                            temps["VRM Temperature (°C)"] = sensor.Value
            except Exception:
                pass

        # fallback if no data
        if all(v is None for v in temps.values()):
            temps["CPU Temperature (°C)"] = "N/A"

    except Exception as e:
        temps["Error"] = str(e)

    return temps


if __name__ == "__main__":
    print(get_temperatures())


def get_all_hwmon_sensors():
    """Return a mapping of hwmon dirs to their temp labels and values.

    Useful for debugging which sensors exist on this machine so RAM/VRM
    sensors can be mapped correctly.
    """
    results = {}
    try:
        for hw in sorted(glob.glob('/sys/class/hwmon/hwmon*')):
            info = {'name': None, 'temps': []}
            name_file = os.path.join(hw, 'name')
            try:
                if os.path.exists(name_file):
                    info['name'] = open(name_file, 'r').read().strip()
            except Exception:
                info['name'] = None

            for tfile in sorted(glob.glob(os.path.join(hw, 'temp*_input'))):
                label = None
                label_file = tfile.replace('_input', '_label')
                try:
                    if os.path.exists(label_file):
                        label = open(label_file, 'r').read().strip()
                except Exception:
                    label = None

                try:
                    val = open(tfile, 'r').read().strip()
                    if val:
                        t = float(val)
                        if t > 1000:
                            t = t / 1000.0
                        t = round(t, 1)
                    else:
                        t = None
                except Exception:
                    t = None

                info['temps'].append({'file': tfile, 'label': label, 'value': t})

            results[hw] = info
    except Exception as e:
        results['error'] = str(e)
    return results
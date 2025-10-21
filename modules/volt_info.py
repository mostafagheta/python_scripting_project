"""
power_info.py
-------------
Module to collect voltage and power consumption info for CPU & GPU.
Cross-platform where possible. Returns structured dictionary.
"""

import platform
import psutil
import subprocess
import os
import glob
import re

def get_power_info():
    data = {
        "CPU Voltage (V)": None,
        "GPU Voltage (V)": None,
        "Total Power Consumption (W)": None
    }

    try:
        system = platform.system().lower()

        # --- Linux implementation ---
        if system == "linux":
            # Try parsing 'sensors' command output if available
            try:
                output = subprocess.check_output(["sensors"]).decode()
                for line in output.splitlines():
                    line = line.strip()
                    if any(x in line.lower() for x in ["vcore", "vcpu", "in0"]):
                        try:
                            data["CPU Voltage (V)"] = float(line.split(":")[1].split()[0])
                            break
                        except Exception:
                            pass
            except Exception:
                pass

            # Estimate power from battery (if laptop)
            try:
                battery = psutil.sensors_battery()
                if battery:
                    data["Total Power Consumption (W)"] = round(battery.percent / 100 * 65, 1)  # rough estimate
            except Exception:
                pass

            # Try reading voltages from hwmon in sysfs: in*_input and in*_label
            try:
                for hw in glob.glob('/sys/class/hwmon/hwmon*'):
                    for infile in glob.glob(os.path.join(hw, 'in*_input')):
                        label_file = infile.replace('_input', '_label')
                        label = None
                        try:
                            if os.path.exists(label_file):
                                label = open(label_file, 'r').read().strip().lower()
                        except Exception:
                            label = None

                        try:
                            val = open(infile, 'r').read().strip()
                            if not val:
                                continue
                            v = float(val)
                            # sysfs may report millivolts for some sensors
                            if v > 100:
                                v = v / 1000.0
                        except Exception:
                            continue

                        # map labels
                        lname = label or ''
                        if any(x in lname for x in ['vcore', 'vcpu', 'cpu-voltage', 'in0']):
                            if data.get('CPU Voltage (V)') is None:
                                data['CPU Voltage (V)'] = round(v, 3)
                        if any(x in lname for x in ['vgpu', 'gpu-voltage', 'in1']):
                            if data.get('GPU Voltage (V)') is None:
                                data['GPU Voltage (V)'] = round(v, 3)
                        # fallback: if label contains 'voltage' and we don't have cpu set, use it
                        if 'voltage' in lname and data.get('CPU Voltage (V)') is None:
                            data['CPU Voltage (V)'] = round(v, 3)
            except Exception:
                pass

        # --- Windows implementation ---
        elif system == "windows":
            try:
                import wmi
                w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                sensors = w.Sensor()
                for sensor in sensors:
                    if sensor.SensorType == u'Voltage':
                        if "cpu" in sensor.Name.lower():
                            data["CPU Voltage (V)"] = sensor.Value
                        elif "gpu" in sensor.Name.lower():
                            data["GPU Voltage (V)"] = sensor.Value
                    elif sensor.SensorType == u'Power':
                        data["Total Power Consumption (W)"] = sensor.Value
            except Exception:
                pass

        # fallback
        if all(v is None for v in data.values()):
            data["CPU Voltage (V)"] = "N/A"

    except Exception as e:
        data["Error"] = str(e)

    return data


if __name__ == "__main__":
    print(get_power_info())


def get_voltages():
    """Compatibility wrapper: return voltages dict expected by main.py."""
    info = get_power_info()
    return {
        'cpu_voltage': info.get('CPU Voltage (V)'),
        'gpu_voltage': info.get('GPU Voltage (V)')
    }


def get_power():
    """Compatibility wrapper: return power info expected by main.py."""
    info = get_power_info()
    return {'total_power_w': info.get('Total Power Consumption (W)')}

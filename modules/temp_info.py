"""
Temperature Monitoring Module
Provides comprehensive temperature monitoring for CPU, GPU, RAM, VRM, and other system components.
"""

import subprocess
import platform
import os
import glob
import re
from . import gpu_info as _gpu_info
from typing import Dict, List, Optional, Tuple


def get_temperatures() -> Dict:
    """
    Get comprehensive temperature information from all available sensors.
    
    Returns:
        Dict containing temperature information organized by component type
    """
    temperatures = {
        "cpu": [],
        "gpu": [],
        "memory": [],
        "vrm": [],
        "motherboard": [],
        "storage": [],
        "other": []
    }
    
    try:
        if platform.system() == "Linux":
            # Get temperatures from hwmon
            hwmon_temps = _get_hwmon_temperatures()
            
            # Get temperatures from sensors command
            sensors_temps = _get_sensors_temperatures()
            
            # Get CPU temperatures specifically
            cpu_temps = _get_cpu_temperatures()
            
            # Get GPU temperatures
            gpu_temps = _get_gpu_temperatures()
            
            # Organize temperatures by component type
            temperatures.update({
                "cpu": cpu_temps,
                "gpu": gpu_temps,
                "hwmon": hwmon_temps,
                "sensors": sensors_temps
            })
        
        elif platform.system() == "Windows":
            # Windows temperature monitoring
            temperatures = _get_windows_temperatures()
    
    except Exception as e:
        temperatures["error"] = f"Failed to get temperatures: {str(e)}"
    
    return temperatures


def _get_hwmon_temperatures() -> List[Dict]:
    """Get temperatures from hwmon sensors."""
    temperatures = []
    
    try:
        hwmon_path = "/sys/class/hwmon"
        if os.path.exists(hwmon_path):
            for hwmon_dir in os.listdir(hwmon_path):
                hwmon_full_path = os.path.join(hwmon_path, hwmon_dir)
                if os.path.isdir(hwmon_full_path):
                    try:
                        # Read sensor name
                        name_file = os.path.join(hwmon_full_path, "name")
                        sensor_name = "Unknown"
                        if os.path.exists(name_file):
                            with open(name_file, "r") as f:
                                sensor_name = f.read().strip()
                        
                        # Find temperature files
                        temp_files = []
                        for file in os.listdir(hwmon_full_path):
                            if file.startswith("temp") and file.endswith("_input"):
                                temp_files.append(file)
                        
                        for temp_file in temp_files:
                            temp_path = os.path.join(hwmon_full_path, temp_file)
                            try:
                                with open(temp_path, "r") as f:
                                    temp_value = float(f.read().strip()) / 1000  # Convert mC to C
                                
                                # Try to get label
                                label_file = temp_file.replace("_input", "_label")
                                label_path = os.path.join(hwmon_full_path, label_file)
                                label = temp_file
                                if os.path.exists(label_path):
                                    with open(label_path, "r") as f:
                                        label = f.read().strip()
                                
                                # Try to get critical and max temperatures
                                crit_file = temp_file.replace("_input", "_crit")
                                max_file = temp_file.replace("_input", "_max")
                                
                                crit_temp = None
                                max_temp = None
                                
                                if os.path.exists(os.path.join(hwmon_full_path, crit_file)):
                                    try:
                                        with open(os.path.join(hwmon_full_path, crit_file), "r") as f:
                                            crit_temp = float(f.read().strip()) / 1000
                                    except Exception:
                                        pass
                                
                                if os.path.exists(os.path.join(hwmon_full_path, max_file)):
                                    try:
                                        with open(os.path.join(hwmon_full_path, max_file), "r") as f:
                                            max_temp = float(f.read().strip()) / 1000
                                    except Exception:
                                        pass
                                
                                temp_info = {
                                    "sensor": sensor_name,
                                    "label": label,
                                    "temperature": temp_value,
                                    "critical": crit_temp,
                                    "max": max_temp,
                                    "file": temp_file
                                }
                                
                                temperatures.append(temp_info)
                                
                            except Exception:
                                continue
                    
                    except Exception:
                        continue
    
    except Exception:
        pass
    
    return temperatures


def _get_sensors_temperatures() -> List[Dict]:
    """Get temperatures using the sensors command."""
    temperatures = []
    
    try:
        result = subprocess.run(['sensors', '-A'], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            content = result.stdout
            current_sensor = None
            
            for line in content.split('\n'):
                line = line.strip()
                
                if line and not line.startswith('Adapter:'):
                    if ':' in line and not line.startswith(' '):
                        # New sensor section
                        current_sensor = line.replace(':', '')
                    elif line.startswith(' ') and ':' in line:
                        # Temperature reading
                        if current_sensor:
                            parts = line.strip().split(':')
                            if len(parts) >= 2:
                                label = parts[0].strip()
                                temp_part = parts[1].strip()
                                
                                # Extract temperature value
                                temp_match = re.search(r'(\d+\.?\d*)°?C', temp_part)
                                if temp_match:
                                    temp_value = float(temp_match.group(1))
                                    
                                    # Extract critical and max if available
                                    crit_match = re.search(r'crit = (\d+\.?\d*)°?C', temp_part)
                                    max_match = re.search(r'max = (\d+\.?\d*)°?C', temp_part)
                                    
                                    crit_temp = float(crit_match.group(1)) if crit_match else None
                                    max_temp = float(max_match.group(1)) if max_match else None
                                    
                                    temp_info = {
                                        "sensor": current_sensor,
                                        "label": label,
                                        "temperature": temp_value,
                                        "critical": crit_temp,
                                        "max": max_temp,
                                        "raw": temp_part
                                    }
                                    
                                    temperatures.append(temp_info)
    
    except Exception:
        pass
    
    return temperatures


def _get_cpu_temperatures() -> List[Dict]:
    """Get CPU-specific temperatures."""
    cpu_temps = []
    
    try:
        # Get temperatures from hwmon for CPU
        hwmon_temps = _get_hwmon_temperatures()
        
        for temp in hwmon_temps:
            sensor_name = temp["sensor"].lower()
            label = temp["label"].lower()
            
            if ("cpu" in sensor_name or "core" in sensor_name or 
                "cpu" in label or "core" in label or 
                "package" in label):
                cpu_temps.append(temp)
        
        # Try to get CPU temperature from thermal zones
        thermal_temps = _get_thermal_zone_temperatures()
        cpu_temps.extend(thermal_temps)
    
    except Exception:
        pass
    
    return cpu_temps


def _get_gpu_temperatures() -> List[Dict]:
    """Get GPU-specific temperatures."""
    gpu_temps = []
    
    try:
        # Get temperatures from hwmon for GPU
        hwmon_temps = _get_hwmon_temperatures()
        
        for temp in hwmon_temps:
            sensor_name = temp["sensor"].lower()
            label = temp["label"].lower()
            
            if ("gpu" in sensor_name or "nvidia" in sensor_name or 
                "amd" in sensor_name or "radeon" in sensor_name or
                "gpu" in label or "nvidia" in label or 
                "amd" in label or "radeon" in label):
                gpu_temps.append(temp)
        
        # Try NVIDIA-specific temperature
        nvidia_temp = _get_nvidia_temperature()
        if nvidia_temp:
            gpu_temps.append(nvidia_temp)

        # fallback: use gpu_info module which may detect GPU temps via other paths
        try:
            ginfo = _gpu_info.get_gpu_info()
            gt = ginfo.get('Temperature')
            if gt:
                # parse numeric part
                m = re.search(r'([0-9]+\.?[0-9]*)', str(gt))
                if m:
                    gpu_temps.append({
                        'sensor': 'gpu_info',
                        'label': ginfo.get('Name') or 'GPU',
                        'temperature': float(m.group(1)),
                        'critical': None,
                        'max': None,
                        'file': 'gpu_info'
                    })
        except Exception:
            pass
    
    except Exception:
        pass
    
    return gpu_temps


def _get_thermal_zone_temperatures() -> List[Dict]:
    """Get temperatures from thermal zones."""
    temps = []
    
    try:
        thermal_path = "/sys/class/thermal"
        if os.path.exists(thermal_path):
            for thermal_dir in os.listdir(thermal_path):
                if thermal_dir.startswith("thermal_zone"):
                    thermal_full_path = os.path.join(thermal_path, thermal_dir)
                    
                    try:
                        # Read temperature
                        temp_file = os.path.join(thermal_full_path, "temp")
                        if os.path.exists(temp_file):
                            with open(temp_file, "r") as f:
                                temp_value = float(f.read().strip()) / 1000  # Convert mC to C
                            
                            # Read type
                            type_file = os.path.join(thermal_full_path, "type")
                            thermal_type = "Unknown"
                            if os.path.exists(type_file):
                                with open(type_file, "r") as f:
                                    thermal_type = f.read().strip()
                            
                            temp_info = {
                                "sensor": f"thermal_zone_{thermal_dir.split('_')[-1]}",
                                "label": thermal_type,
                                "temperature": temp_value,
                                "critical": None,
                                "max": None,
                                "file": "thermal_zone"
                            }
                            
                            temps.append(temp_info)
                    
                    except Exception:
                        continue
    
    except Exception:
        pass
    
    return temps


def _get_nvidia_temperature() -> Optional[Dict]:
    """Get NVIDIA GPU temperature using nvidia-smi."""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            temp_value = float(result.stdout.strip())
            return {
                "sensor": "nvidia-smi",
                "label": "GPU Temperature",
                "temperature": temp_value,
                "critical": None,
                "max": None,
                "file": "nvidia-smi"
            }
    
    except Exception:
        pass
    
    return None


def _get_windows_temperatures() -> Dict:
    """Get temperatures on Windows (placeholder)."""
    return {
        "cpu": [],
        "gpu": [],
        "memory": [],
        "vrm": [],
        "motherboard": [],
        "storage": [],
        "other": [],
        "note": "Windows temperature monitoring not implemented"
    }


def get_all_hwmon_sensors() -> Dict:
    """
    Diagnostic helper that lists all hwmon sensors and their values.
    
    Returns:
        Dict containing all hwmon sensor information
    """
    sensors = {}
    
    try:
        hwmon_path = "/sys/class/hwmon"
        if os.path.exists(hwmon_path):
            for hwmon_dir in os.listdir(hwmon_path):
                hwmon_full_path = os.path.join(hwmon_path, hwmon_dir)
                if os.path.isdir(hwmon_full_path):
                    sensor_info = {}
                    
                    try:
                        # Read sensor name
                        name_file = os.path.join(hwmon_full_path, "name")
                        if os.path.exists(name_file):
                            with open(name_file, "r") as f:
                                sensor_info["name"] = f.read().strip()
                        
                        # List all files in the sensor directory
                        sensor_files = {}
                        for file in os.listdir(hwmon_full_path):
                            if file.endswith("_input") or file.endswith("_label") or file.endswith("_crit") or file.endswith("_max"):
                                file_path = os.path.join(hwmon_full_path, file)
                                try:
                                    with open(file_path, 'r') as fh:
                                        raw = fh.read().strip()
                                except Exception:
                                    sensor_files[file] = "Error reading"
                                    continue

                                # normalize numeric values where appropriate
                                val = raw
                                try:
                                    # integer-only values
                                    if re.match(r'^-?\d+$', raw):
                                        num = float(raw)
                                        if file.startswith('temp'):
                                            # hwmon temps are typically millidegrees
                                            val = round(num / 1000.0, 1)
                                        elif file.startswith('in') or file.startswith('curr'):
                                            # leave as numeric (units vary by sensor)
                                            val = round(num, 3)
                                        else:
                                            val = num
                                    # float values
                                    elif re.match(r'^-?\d+\.\d+$', raw):
                                        val = float(raw)
                                except Exception:
                                    val = raw

                                sensor_files[file] = val
                        
                        sensor_info["files"] = sensor_files
                        sensors[hwmon_dir] = sensor_info
                    
                    except Exception:
                        sensors[hwmon_dir] = {"error": "Failed to read sensor"}
    
    except Exception:
        sensors["error"] = "Failed to access hwmon"
    
    return sensors


def get_temperature_summary() -> Dict:
    """
    Get a summary of current temperatures with critical alerts.
    
    Returns:
        Dict containing temperature summary
    """
    temps = get_temperatures()
    summary = {
        "cpu_max": None,
        "gpu_max": None,
        "critical_alerts": [],
        "total_sensors": 0
    }
    
    try:
        all_temps = []
        
        # Collect all temperatures
        for category, temp_list in temps.items():
            if isinstance(temp_list, list):
                all_temps.extend(temp_list)
        
        summary["total_sensors"] = len(all_temps)
        
        # Find maximum temperatures
        cpu_temps = [t["temperature"] for t in all_temps if "cpu" in t.get("sensor", "").lower() or "core" in t.get("label", "").lower()]
        gpu_temps = [t["temperature"] for t in all_temps if "gpu" in t.get("sensor", "").lower() or "gpu" in t.get("label", "").lower()]
        
        if cpu_temps:
            summary["cpu_max"] = max(cpu_temps)
        
        if gpu_temps:
            summary["gpu_max"] = max(gpu_temps)
        
        # Check for critical temperatures
        for temp in all_temps:
            if temp.get("critical") and temp["temperature"] >= temp["critical"]:
                summary["critical_alerts"].append({
                    "sensor": temp["sensor"],
                    "label": temp["label"],
                    "temperature": temp["temperature"],
                    "critical": temp["critical"]
                })
    
    except Exception:
        pass
    
    return summary


def get_quick_summary() -> Dict[str, Optional[float]]:
    """Return a compact summary with four key temperatures.

    Keys:
        - CPU Temperature (°C): package or max core
        - GPU Temperature (°C): best GPU reading
        - RAM Temperature (°C): best matching hwmon label if available
        - VRM Temperature (°C): best matching hwmon label if available
    """
    temps = get_temperatures()
    quick = {
        'CPU Temperature (°C)': None,
        'GPU Temperature (°C)': None,
        'RAM Temperature (°C)': None,
        'VRM Temperature (°C)': None,
    }

    try:
        # CPU: prefer package id, else max core
        cpu_list = temps.get('cpu') or []
        if cpu_list:
            pkg = next((t for t in cpu_list if 'package' in t.get('label', '').lower()), None)
            if pkg:
                quick['CPU Temperature (°C)'] = pkg.get('temperature')
            else:
                # pick max temperature
                vals = [t.get('temperature') for t in cpu_list if isinstance(t.get('temperature'), (int, float))]
                if vals:
                    quick['CPU Temperature (°C)'] = max(vals)

        # GPU: use gpu list or hwmon nvidia
        gpu_list = temps.get('gpu') or []
        if gpu_list:
            vals = [t.get('temperature') for t in gpu_list if isinstance(t.get('temperature'), (int, float))]
            if vals:
                quick['GPU Temperature (°C)'] = max(vals)

        # RAM/VRM: look through hwmon entries for likely labels
        hwmon = temps.get('hwmon') or []
        for entry in hwmon:
            label = (entry.get('label') or '').lower()
            sensor = (entry.get('sensor') or '').lower()
            temp_val = entry.get('temperature')
            if not isinstance(temp_val, (int, float)):
                continue
            if any(x in label or x in sensor for x in ['dram', 'dram', 'memory', 'mem', 'ram']):
                if quick['RAM Temperature (°C)'] is None:
                    quick['RAM Temperature (°C)'] = temp_val
            if any(x in label or x in sensor for x in ['vrm', 'vreg', 'vcore']):
                if quick['VRM Temperature (°C)'] is None:
                    quick['VRM Temperature (°C)'] = temp_val

        # Fallback: if RAM/VRM still None, try acpitz heuristics
        if quick['RAM Temperature (°C)'] is None:
            for entry in hwmon:
                if 'acpitz' in (entry.get('sensor') or '').lower() and entry.get('temperature') and entry.get('temperature') > 0:
                    quick['RAM Temperature (°C)'] = entry.get('temperature')
                    break
        if quick['VRM Temperature (°C)'] is None:
            for entry in hwmon:
                if 'acpitz' in (entry.get('sensor') or '').lower() and entry.get('temperature') and entry.get('temperature') > 0:
                    quick['VRM Temperature (°C)'] = entry.get('temperature')
                    break

    except Exception:
        pass

    return quick


if __name__ == "__main__":
    # Test the module
    temps = get_temperatures()
    print("Temperature Information:")
    for category, temp_list in temps.items():
        if isinstance(temp_list, list) and temp_list:
            print(f"\n{category.upper()}:")
            for temp in temp_list:
                print(f"  {temp['sensor']} - {temp['label']}: {temp['temperature']:.1f}°C")
    
    print(f"\nTemperature Summary:")
    summary = get_temperature_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    print(f"\nAll HWMON Sensors:")
    sensors = get_all_hwmon_sensors()
    for sensor_id, sensor_info in sensors.items():
        print(f"{sensor_id}: {sensor_info}")

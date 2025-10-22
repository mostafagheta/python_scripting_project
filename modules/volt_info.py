

import subprocess
import platform
import os
import glob
import re
from typing import Dict, List, Optional


def get_voltages() -> Dict:
    """
    Get real-time voltage values from all available sensors.
    
    Returns:
        Dict containing voltage information
    """
    voltages = {
        "cpu": [],
        "gpu": [],
        "memory": [],
        "motherboard": [],
        "other": []
    }
    
    try:
        if platform.system() == "Linux":
            # Get voltages from hwmon
            hwmon_voltages = _get_hwmon_voltages()
            
            # Get voltages from sensors command
            sensors_voltages = _get_sensors_voltages()
            
            # Get CPU voltages specifically
            cpu_voltages = _get_cpu_voltages()
            
            # Get GPU voltages
            gpu_voltages = _get_gpu_voltages()
            
            voltages.update({
                "cpu": cpu_voltages,
                "gpu": gpu_voltages,
                "hwmon": hwmon_voltages,
                "sensors": sensors_voltages
            })
        
        elif platform.system() == "Windows":
            voltages = _get_windows_voltages()
    
    except Exception as e:
        voltages["error"] = f"Failed to get voltages: {str(e)}"
    
    return voltages


def get_power() -> Dict:
    """
    Get power consumption information from all available sources.
    
    Returns:
        Dict containing power consumption information
    """
    power_info = {
        "cpu": [],
        "gpu": [],
        "system": [],
        "total": None
    }
    
    try:
        if platform.system() == "Linux":
            # Get power from hwmon
            hwmon_power = _get_hwmon_power()
            
            # Get power from RAPL
            rapl_power = _get_rapl_power()
            
            # Get GPU power
            gpu_power = _get_gpu_power()
            
            power_info.update({
                "cpu": rapl_power.get("cpu", []),
                "gpu": gpu_power,
                "hwmon": hwmon_power,
                "rapl": rapl_power
            })
            
            # Calculate total power if possible
            total_power = _calculate_total_power(power_info)
            power_info["total"] = total_power
        
        elif platform.system() == "Windows":
            power_info = _get_windows_power()
    
    except Exception as e:
        power_info["error"] = f"Failed to get power info: {str(e)}"
    
    return power_info


def get_power_info() -> Dict:
    """
    Get comprehensive power and voltage information.
    
    Returns:
        Dict containing both voltage and power information
    """
    return {
        "voltages": get_voltages(),
        "power": get_power()
    }


def _get_hwmon_voltages() -> List[Dict]:
    """Get voltages from hwmon sensors."""
    voltages = []
    
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
                        
                        # Find voltage files
                        voltage_files = []
                        for file in os.listdir(hwmon_full_path):
                            if file.startswith("in") and file.endswith("_input"):
                                voltage_files.append(file)
                        
                        for voltage_file in voltage_files:
                            voltage_path = os.path.join(hwmon_full_path, voltage_file)
                            try:
                                with open(voltage_path, "r") as f:
                                    voltage_value = float(f.read().strip()) / 1000  # Convert mV to V
                                
                                # Try to get label
                                label_file = voltage_file.replace("_input", "_label")
                                label_path = os.path.join(hwmon_full_path, label_file)
                                label = voltage_file
                                if os.path.exists(label_path):
                                    with open(label_path, "r") as f:
                                        label = f.read().strip()
                                
                                voltage_info = {
                                    "sensor": sensor_name,
                                    "label": label,
                                    "voltage": voltage_value,
                                    "file": voltage_file
                                }
                                
                                voltages.append(voltage_info)
                                
                            except Exception:
                                continue
                    
                    except Exception:
                        continue
    
    except Exception:
        pass
    
    return voltages


def _get_sensors_voltages() -> List[Dict]:
    """Get voltages using the sensors command."""
    voltages = []
    
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
                        # Voltage reading
                        if current_sensor:
                            parts = line.strip().split(':')
                            if len(parts) >= 2:
                                label = parts[0].strip()
                                voltage_part = parts[1].strip()
                                
                                # Extract voltage value
                                voltage_match = re.search(r'(\d+\.?\d*)V', voltage_part)
                                if voltage_match:
                                    voltage_value = float(voltage_match.group(1))
                                    
                                    voltage_info = {
                                        "sensor": current_sensor,
                                        "label": label,
                                        "voltage": voltage_value,
                                        "raw": voltage_part
                                    }
                                    
                                    voltages.append(voltage_info)
    
    except Exception:
        pass
    
    return voltages


def _get_cpu_voltages() -> List[Dict]:
    """Get CPU-specific voltages."""
    cpu_voltages = []
    
    try:
        hwmon_voltages = _get_hwmon_voltages()
        
        for voltage in hwmon_voltages:
            sensor_name = voltage["sensor"].lower()
            label = voltage["label"].lower()
            
            if ("cpu" in sensor_name or "core" in sensor_name or 
                "cpu" in label or "core" in label or 
                "vcore" in label):
                cpu_voltages.append(voltage)
    
    except Exception:
        pass
    
    return cpu_voltages


def _get_gpu_voltages() -> List[Dict]:
    """Get GPU-specific voltages."""
    gpu_voltages = []
    
    try:
        hwmon_voltages = _get_hwmon_voltages()
        
        for voltage in hwmon_voltages:
            sensor_name = voltage["sensor"].lower()
            label = voltage["label"].lower()
            
            if ("gpu" in sensor_name or "nvidia" in sensor_name or 
                "amd" in sensor_name or "radeon" in sensor_name or
                "gpu" in label or "nvidia" in label or 
                "amd" in label or "radeon" in label):
                gpu_voltages.append(voltage)
    
    except Exception:
        pass
    
    return gpu_voltages


def _get_hwmon_power() -> List[Dict]:
    """Get power consumption from hwmon sensors."""
    power_info = []
    
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
                        
                        # Find power files
                        power_files = []
                        for file in os.listdir(hwmon_full_path):
                            if file.startswith("power") and file.endswith("_input"):
                                power_files.append(file)
                        
                        for power_file in power_files:
                            power_path = os.path.join(hwmon_full_path, power_file)
                            try:
                                with open(power_path, "r") as f:
                                    power_value = float(f.read().strip()) / 1000000  # Convert μW to W
                                
                                # Try to get label
                                label_file = power_file.replace("_input", "_label")
                                label_path = os.path.join(hwmon_full_path, label_file)
                                label = power_file
                                if os.path.exists(label_path):
                                    with open(label_path, "r") as f:
                                        label = f.read().strip()
                                
                                power_data = {
                                    "sensor": sensor_name,
                                    "label": label,
                                    "power": power_value,
                                    "file": power_file
                                }
                                
                                power_info.append(power_data)
                                
                            except Exception:
                                continue
                    
                    except Exception:
                        continue
    
    except Exception:
        pass
    
    return power_info


def _get_rapl_power() -> Dict:
    """Get power information from RAPL (Running Average Power Limit)."""
    rapl_info = {"cpu": [], "system": []}
    
    try:
        rapl_path = "/sys/class/powercap/intel-rapl"
        if os.path.exists(rapl_path):
            for rapl_dir in os.listdir(rapl_path):
                if rapl_dir.startswith("intel-rapl:"):
                    rapl_full_path = os.path.join(rapl_path, rapl_dir)
                    
                    try:
                        # Read name
                        name_file = os.path.join(rapl_full_path, "name")
                        rapl_name = "Unknown"
                        if os.path.exists(name_file):
                            with open(name_file, "r") as f:
                                rapl_name = f.read().strip()
                        
                        # Read power
                        power_file = os.path.join(rapl_full_path, "energy_uj")
                        if os.path.exists(power_file):
                            with open(power_file, "r") as f:
                                # energy is reported in microjoules (μJ)
                                energy_uj = int(f.read().strip())
                                # Convert μJ -> J
                                energy_j = energy_uj / 1_000_000

                            # RAPL exposes cumulative energy. Without sampling over time
                            # we cannot compute an instantaneous Watt value reliably here.
                            # So return the cumulative energy in joules and leave
                            # 'power' as None to avoid misrepresenting the metric.
                            power_data = {
                                "name": rapl_name,
                                "power": None,
                                "energy_j": energy_j,
                                "note": "energy is cumulative; sample over time to compute watts"
                            }
                            
                            if "package" in rapl_name.lower() or "cpu" in rapl_name.lower():
                                rapl_info["cpu"].append(power_data)
                            else:
                                rapl_info["system"].append(power_data)
                    
                    except Exception:
                        continue
    
    except Exception:
        pass
    
    return rapl_info


def _get_gpu_power() -> List[Dict]:
    """Get GPU power consumption."""
    gpu_power = []
    
    try:
        # Try NVIDIA first
        result = subprocess.run(['nvidia-smi', '--query-gpu=index,power.draw', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = [part.strip() for part in line.split(',')]
                    if len(parts) >= 2:
                        gpu_data = {
                            "index": int(parts[0]),
                            "vendor": "NVIDIA",
                            "power": float(parts[1]) if parts[1] != 'N/A' else None
                        }
                        gpu_power.append(gpu_data)
    
    except Exception:
        pass
    
    return gpu_power


def _calculate_total_power(power_info: Dict) -> Optional[float]:
    """Calculate total system power consumption."""
    try:
        total_power = 0.0
        
        # Add CPU power
        for cpu_power in power_info.get("cpu", []):
            if isinstance(cpu_power, dict) and "power" in cpu_power:
                total_power += cpu_power["power"]
        
        # Add GPU power
        for gpu_power in power_info.get("gpu", []):
            if isinstance(gpu_power, dict) and "power" in gpu_power and gpu_power["power"]:
                total_power += gpu_power["power"]
        
        # Add hwmon power
        for hwmon_power in power_info.get("hwmon", []):
            if isinstance(hwmon_power, dict) and "power" in hwmon_power:
                total_power += hwmon_power["power"]
        
        return total_power if total_power > 0 else None
    
    except Exception:
        return None


def _get_windows_voltages() -> Dict:
    """Get voltages on Windows (placeholder)."""
    return {
        "cpu": [],
        "gpu": [],
        "memory": [],
        "motherboard": [],
        "other": [],
        "note": "Windows voltage monitoring not implemented"
    }


def _get_windows_power() -> Dict:
    """Get power information on Windows (placeholder)."""
    return {
        "cpu": [],
        "gpu": [],
        "system": [],
        "total": None,
        "note": "Windows power monitoring not implemented"
    }


def _fmt_float(val: float, unit: str = "") -> str:
    try:
        if val is None:
            return "N/A"
        return f"{val:.3f}{unit}"
    except Exception:
        return str(val)


def get_voltages_display() -> Dict[str, list]:
    """Return voltages formatted for GUI display.

    Returns a dict mapping category names to a list of human-readable strings.
    Categories with no usable data are omitted.
    """
    raw = get_voltages()
    display = {}

    for category, items in raw.items():
        if not items or not isinstance(items, list):
            continue

        lines = []
        for it in items:
            try:
                sensor = it.get("sensor", "")
                label = it.get("label") or it.get("file") or ""
                voltage = it.get("voltage")

                if voltage is None:
                    # sometimes sensors returns raw strings in 'raw'
                    raw_part = it.get("raw")
                    if raw_part:
                        lines.append(f"{sensor} {label} — {raw_part}")
                    continue

                lines.append(f"{sensor} {label} — {_fmt_float(voltage, ' V')}")
            except Exception:
                continue

        if lines:
            display[category] = lines

    return display


def get_power_display() -> Dict[str, list]:
    """Return power info formatted for GUI display.

    - Shows instantaneous watts when available (hwmon or nvidia-smi).
    - Shows cumulative energy in joules for RAPL entries, with a note that
      energy is cumulative and requires sampling to compute watts.
    """
    raw = get_power()
    display = {}

    # sections to prefer ordering
    sections = ["cpu", "gpu", "hwmon", "rapl", "system"]

    for section in sections:
        items = raw.get(section, [])
        if not items or not isinstance(items, list):
            continue

        lines = []
        for it in items:
            try:
                name = it.get("name") or it.get("sensor") or str(it.get("index", ""))
                if it.get("power") is not None:
                    lines.append(f"{name} — {_fmt_float(it['power'], ' W')}")
                elif it.get("energy_j") is not None:
                    lines.append(f"{name} — {_fmt_float(it['energy_j'], ' J')} (cumulative)")
                else:
                    # No usable numeric data
                    continue
            except Exception:
                continue

        if lines:
            display[section] = lines

    # total
    total = raw.get("total")
    if total:
        display["total"] = [f"{total:.2f} W"]

    return display


def get_volt_power_panel() -> list:
    """Return a list of lines forming the panel requested by the GUI.

    The layout matches:
    Voltages & Power
    	•	Real-time voltage values :
    	•	Power consumption :

    Each bullet will be followed by indented sensor lines (if any).
    """
    panel = []
    panel.append("Voltages & Power")

    volt_disp = get_voltages_display()
    power_disp = get_power_display()

    # Voltages bullet
    panel.append("\t•\tReal-time voltage values :")
    if volt_disp:
        for section, lines in volt_disp.items():
            panel.append(f"\t\t- {section}:")
            for l in lines:
                panel.append(f"\t\t\t{l}")
    else:
        panel.append("\t\t- No voltage sensors detected or accessible")

    # Power bullet
    panel.append("\t•\tPower consumption :")
    if power_disp:
        for section, lines in power_disp.items():
            panel.append(f"\t\t- {section}:")
            for l in lines:
                panel.append(f"\t\t\t{l}")
    else:
        panel.append("\t\t- No instantaneous power readings available; see cumulative RAPL energy where present")

    return panel


def _compact_join(items: list, max_items: int = 5) -> str:
    if not items:
        return "None"
    parts = []
    for it in items[:max_items]:
        # item may be dict or string
        if isinstance(it, dict):
            label = it.get("label") or it.get("file") or it.get("name") or it.get("sensor")
            val = it.get("voltage") or it.get("power") or it.get("energy_j")
            if val is None:
                parts.append(f"{label}: N/A")
            else:
                # choose unit
                if "voltage" in it or label and label.startswith("in"):
                    parts.append(f"{label}: {_fmt_float(val, ' V')}")
                elif "power" in it:
                    parts.append(f"{label}: {_fmt_float(val, ' W')}")
                elif "energy_j" in it:
                    parts.append(f"{label}: {_fmt_float(val, ' J')}")
                else:
                    parts.append(f"{label}: {val}")
        else:
            parts.append(str(it))

    if len(items) > max_items:
        parts.append("...")
    return ", ".join(parts)


def get_volt_power_summary() -> list:
    """Return two short lines suitable for a compact GUI summary.

    Returns:
      [ "Voltages: ...", "Power: ..." ]
    """
    volt = get_voltages()
    power = get_power()

    # collect voltage readings from sensible categories
    volt_items = []
    for key in ("hwmon", "sensors", "cpu", "gpu", "memory"):
        v = volt.get(key)
        if v:
            volt_items.extend(v)

    volt_line = f"Voltages: {_compact_join(volt_items)}"

    # collect power readings: prefer instantaneous power, else show RAPL energy
    power_items = []
    # GPU/hwmon may contain 'power'
    for key in ("gpu", "hwmon"):
        p = power.get(key)
        if p:
            power_items.extend(p)

    # CPU rapl energy if no instantaneous watts
    if not power_items:
        rapl_cpu = power.get("rapl", {}).get("cpu", [])
        if rapl_cpu:
            power_items.extend(rapl_cpu)

    power_line = f"Power: {_compact_join(power_items)}"

    return [volt_line, power_line]


if __name__ == "__main__":
    # Test the module
    voltages = get_voltages()
    print("Voltage Information:")
    for category, voltage_list in voltages.items():
        if isinstance(voltage_list, list) and voltage_list:
            print(f"\n{category.upper()}:")
            for voltage in voltage_list:
                print(f"  {voltage['sensor']} - {voltage['label']}: {voltage['voltage']:.3f}V")
    
    power = get_power()
    print(f"\nPower Information:")
    for category, power_list in power.items():
        if isinstance(power_list, list) and power_list:
            print(f"\n{category.upper()}:")
            for pwr in power_list:
                if "power" in pwr:
                    print(f"  {pwr.get('sensor', pwr.get('name', 'Unknown'))}: {pwr['power']:.2f}W")
    
    if power.get("total"):
        print(f"\nTotal System Power: {power['total']:.2f}W")

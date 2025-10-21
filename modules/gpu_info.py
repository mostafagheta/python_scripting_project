# system_info/gpu_info.py
import subprocess
import os
import glob
import re


def _read_first_temp_from_hwmon(path):
    try:
        # find tempN_input files
        files = sorted(glob.glob(os.path.join(path, 'temp*_input')))
        for f in files:
            try:
                v = open(f, 'r').read().strip()
                if v:
                    # temp is usually millidegree or degree depending on sensor
                    t = float(v)
                    # if value looks too large (e.g., >1000), assume millidegree
                    if t > 1000:
                        t = t / 1000.0
                    return round(t, 1)
            except Exception:
                continue
    except Exception:
        return None


def get_gpu_info():
    """Return GPU info including name, vendor, memory, and temperature.

    This function prefers nvidia-smi for NVIDIA cards. For other vendors it
    parses lspci and attempts to read temperatures from DRM hwmon entries.
    For integrated Intel GPUs memory is reported as 'Shared'.
    """
    gpu_info = {"Name": None, "Vendor": None, "Memory": None, "Temperature": None}

    # Try NVIDIA first
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total,temperature.gpu", "--format=csv,noheader,nounits"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        parts = [p.strip() for p in out.strip().split(',')]
        if len(parts) >= 3:
            name = parts[0]
            mem = parts[1]
            temp = parts[2]
            gpu_info.update({
                "Name": name,
                "Vendor": "NVIDIA",
                "Memory": f"{mem} MB",
                "Temperature": f"{temp} °C"
            })
            return gpu_info
    except Exception:
        pass

    # Parse lspci to gather all VGA/3D devices with bus ids and quoted fields
    devices = []
    try:
        out = subprocess.check_output(["lspci", "-mm"], text=True, stderr=subprocess.DEVNULL, timeout=2)
        for line in out.splitlines():
            if 'VGA' in line or '3D' in line:
                parts = line.split()
                bus = parts[0] if parts else None
                matches = re.findall(r'"([^"]+)"', line)
                vendor_field = matches[1] if len(matches) > 1 else ''
                name_field = matches[2] if len(matches) > 2 else ' '.join(parts[1:])
                devices.append({'bus': bus, 'vendor': vendor_field, 'name': name_field})
    except Exception:
        devices = []

    # Choose preferred device: prefer NVIDIA, then AMD/discrete, else first
    preferred = None
    if devices:
        for d in devices:
            if 'nvidia' in (d['vendor'] or '').lower() or 'nvidia' in (d['name'] or '').lower():
                preferred = d
                break
        if not preferred:
            # pick a non-Intel discrete if present
            for d in devices:
                v = (d['vendor'] or '').lower()
                if 'intel' not in v and v:
                    preferred = d
                    break
        if not preferred:
            preferred = devices[0]

    if preferred:
        gpu_info['Name'] = preferred.get('name')
        pv = (preferred.get('vendor') or '').lower()
        if 'nvidia' in pv:
            gpu_info['Vendor'] = 'NVIDIA'
        elif 'amd' in pv or 'ati' in pv or 'advanced micro devices' in pv:
            gpu_info['Vendor'] = 'AMD'
        elif 'intel' in pv:
            gpu_info['Vendor'] = 'Intel'
        else:
            # as a last resort try matching in the name
            nf = (preferred.get('name') or '').lower()
            if 'nvidia' in nf:
                gpu_info['Vendor'] = 'NVIDIA'
            elif 'radeon' in nf or 'amd' in nf or 'ati' in nf:
                gpu_info['Vendor'] = 'AMD'
            elif 'intel' in nf:
                gpu_info['Vendor'] = 'Intel'

    # Try reading DRM hwmon sensors for temperature
    try:
        # Map temps to PCI devices and prefer the preferred device if possible
        temps = {}  # map bus_suffix -> temp
        for card in glob.glob('/sys/class/drm/card*'):
            dev = os.path.join(card, 'device')
            if not os.path.isdir(dev):
                continue
            # resolve path to find the PCI id (e.g., 0000:01:00.0)
            try:
                real = os.path.realpath(dev)
            except Exception:
                real = dev
            # try to extract PCI id patterns like '0000:01:00.0' or '01:00.0'
            m = re.search(r'(?:[0-9a-f]{4}:)?([0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f])', real, re.IGNORECASE)
            bus_suffix = m.group(1) if m else None

            # read hwmon sensors under this device
            for hw in glob.glob(os.path.join(dev, 'hwmon', 'hwmon*')):
                temp = _read_first_temp_from_hwmon(hw)
                if temp is not None:
                    temps[bus_suffix] = temp

        chosen_temp = None
        # prefer temp for preferred device bus
        if preferred and preferred.get('bus'):
            # lspci bus may be like '01:00.0' or '0000:01:00.0'; try to match suffix
            bus = preferred.get('bus')
            if bus in temps:
                chosen_temp = temps[bus]
            else:
                # also try matching only last 7 chars
                short = bus[-7:] if len(bus) >= 7 else bus
                if short in temps:
                    chosen_temp = temps[short]

        # if not found, prefer any NVIDIA temp, else first available
        if chosen_temp is None and temps:
            # try to find a vendor id for each bus and prefer NVIDIA
            def vendor_from_bus(bus_s):
                # try to read /sys/bus/pci/devices/0000:BUS/vendor
                if not bus_s:
                    return None
                # try both with and without domain
                candidates = [bus_s, '0000:' + bus_s]
                for cb in candidates:
                    p = f'/sys/bus/pci/devices/{cb}/vendor'
                    try:
                        with open(p, 'r') as f:
                            v = f.read().strip().lower()
                            if '10de' in v:
                                return 'NVIDIA'
                            if '1002' in v or '1022' in v:
                                return 'AMD'
                            if '8086' in v:
                                return 'Intel'
                    except Exception:
                        continue
                return None

            nvidia_found = None
            for b, t in temps.items():
                if vendor_from_bus(b) == 'NVIDIA':
                    nvidia_found = t
                    break
            if nvidia_found is not None:
                chosen_temp = nvidia_found
            else:
                # pick arbitrary first
                chosen_temp = next(iter(temps.values()))

        if chosen_temp is not None:
            gpu_info['Temperature'] = f"{chosen_temp} °C"
    except Exception:
        pass

    # Memory for integrated GPUs: mark as shared
    if gpu_info.get('Vendor') and gpu_info.get('Vendor').lower() == 'intel':
        gpu_info['Memory'] = 'Shared (system)'

    return gpu_info
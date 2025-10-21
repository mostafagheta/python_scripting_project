import os
import subprocess


def _read_sys(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return None


def _get_chipset_from_lspci():
    try:
        out = subprocess.check_output(['lspci', '-mm'], stderr=subprocess.DEVNULL, text=True, timeout=2)
        # look for common chipset lines: 'Host bridge' or 'ISA bridge' entries
        for line in out.splitlines():
            if 'Host bridge' in line or 'ISA bridge' in line or 'Bridge' in line:
                # return the vendor/device portion
                parts = line.split('"')
                if len(parts) >= 4:
                    return parts[3]
                return line
    except Exception:
        return None


def _get_from_dmidecode():
    # dmidecode typically requires root. Try to run it; if not available or permitted, return None.
    try:
        out = subprocess.check_output(['dmidecode', '-t', '2'], stderr=subprocess.DEVNULL, text=True, timeout=3)
        # parse Manufacturer, Product Name, Version (BIOS info is in type 0/1 but many distros include useful fields)
        res = {}
        for line in out.splitlines():
            line = line.strip()
            if line.startswith('Manufacturer:'):
                res['manufacturer'] = line.split(':', 1)[1].strip()
            elif line.startswith('Product Name:'):
                res['product'] = line.split(':', 1)[1].strip()
            elif line.startswith('Version:') and 'bios' in out.lower():
                # heuristics: sometimes Version here refers to board version
                res['board_version'] = line.split(':', 1)[1].strip()
        # BIOS (type 0 or 1) - try separate call for BIOS
        try:
            bios_out = subprocess.check_output(['dmidecode', '-t', '0'], stderr=subprocess.DEVNULL, text=True, timeout=2)
            for line in bios_out.splitlines():
                line = line.strip()
                if line.startswith('Version:'):
                    res['bios_version'] = line.split(':', 1)[1].strip()
                    break
        except Exception:
            pass

        return res or None
    except Exception:
        return None


def get_motherboard_info():
    info = {}
    # Manufacturer / Board vendor
    vendor = _read_sys('/sys/class/dmi/id/board_vendor') or _read_sys('/sys/class/dmi/id/chassis_vendor')
    product = _read_sys('/sys/class/dmi/id/board_name') or _read_sys('/sys/class/dmi/id/product_name')
    bios_version = _read_sys('/sys/class/dmi/id/bios_version') or _read_sys('/sys/class/dmi/id/bios_date')

    if vendor:
        info['manufacturer'] = vendor
    if product:
        info['product'] = product
    if bios_version:
        info['bios_version'] = bios_version

    # Chipset detection (best-effort)
    chipset = None
    # Some systems expose a chipset file; try a few candidates
    chipset_files = [
        '/sys/class/dmi/id/modalias',
    ]
    for f in chipset_files:
        val = _read_sys(f)
        if val:
            chipset = val
            break

    if not chipset:
        chipset = _get_chipset_from_lspci()

    if chipset:
        info['chipset'] = chipset

    if not info:
        return {'note': 'Motherboard info not available on this platform'}

    return info


if __name__ == '__main__':
    # quick manual test
    print(get_motherboard_info())

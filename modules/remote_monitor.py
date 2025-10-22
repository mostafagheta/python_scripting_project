import json
import re
from fabric import Connection


def _run(conn: Connection, cmd: str, timeout: int = 6) -> str:
    try:
        res = conn.run(cmd, hide=True, warn=True, timeout=timeout)
        return res.stdout.strip()
    except Exception:
        return ""


def _parse_lscpu(text: str) -> dict:
    info = {}
    try:
        if text.strip().startswith("{"):
            data = json.loads(text)
            if isinstance(data, dict) and "lscpu" in data:
                for item in data["lscpu"]:
                    k = item.get("field", "").strip().strip(":")
                    v = item.get("data")
                    info[k] = v
        else:
            for line in text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    info[k.strip()] = v.strip()
    except Exception:
        pass
    cpu = {}
    try:
        cpu["brand"] = info.get("Model name") or info.get("Model Name")
        cpu["arch"] = info.get("Architecture")
        sockets = int((info.get("Socket(s)") or "0").split()[0]) if info.get("Socket(s)") else None
        cores_per_socket = int((info.get("Core(s) per socket") or "0").split()[0]) if info.get("Core(s) per socket") else None
        threads_total = int((info.get("CPU(s)") or "0").split()[0]) if info.get("CPU(s)") else None
        if sockets and cores_per_socket:
            cpu["cores"] = sockets * cores_per_socket
        if threads_total:
            cpu["threads"] = threads_total
    except Exception:
        pass
    return cpu


def _get_os_info(conn: Connection) -> dict:
    # Prefer Python for consistent keys
    py = "python3 - <<'PY'\nimport platform, json\nprint(json.dumps({'OS Name': platform.system(), 'Version': platform.version(), 'Architecture': platform.machine()}))\nPY"
    out = _run(conn, py)
    try:
        if out:
            return json.loads(out)
    except Exception:
        pass
    name = _run(conn, "uname -s")
    ver = _run(conn, "uname -r")
    arch = _run(conn, "uname -m")
    return {"OS Name": name or None, "Version": ver or None, "Architecture": arch or None}


def _get_cpu_info(conn: Connection) -> dict:
    out = _run(conn, "lscpu -J 2>/dev/null || lscpu")
    cpu = _parse_lscpu(out)
    return cpu


def _get_mem_info(conn: Connection) -> dict:
    out = _run(conn, "free -b | awk '/^Mem:/ {print $2}'")
    try:
        total = int(out.strip()) if out.strip().isdigit() else None
        if total is not None:
            return {"Total (GB)": round(total / (1024**3), 2)}
    except Exception:
        pass
    return {"Total (GB)": None}


def _get_gpu_info(conn: Connection) -> dict:
    info = {"Name": None, "Vendor": None, "Memory": None, "Temperature": None}
    nvsmi = _run(conn, "nvidia-smi --query-gpu=name,memory.total,temperature.gpu --format=csv,noheader,nounits")
    if nvsmi:
        try:
            parts = [p.strip() for p in nvsmi.split(',')]
            if len(parts) >= 3:
                info.update({"Name": parts[0], "Vendor": "NVIDIA", "Memory": f"{parts[1]} MB", "Temperature": f"{parts[2]} °C"})
                return info
        except Exception:
            pass
    lspci = _run(conn, "lspci -mm | egrep 'VGA|3D' || true")
    if lspci:
        m = re.findall(r'"([^"]+)"', lspci)
        if len(m) >= 3:
            info["Vendor"] = m[1]
            info["Name"] = m[2]
    return info


def _get_temp_summary(conn: Connection) -> dict:
    quick = {"CPU Temperature (°C)": None, "GPU Temperature (°C)": None, "RAM Temperature (°C)": None, "VRM Temperature (°C)": None}
    sens = _run(conn, "sensors -A 2>/dev/null | egrep -i 'package id|tctl|tdie|cpu temp|cpu:\\s*\\+|core 0' -m 1 || true")
    if sens:
        try:
            m = re.search(r'([0-9]+\.?[0-9]*)\s*°?C', sens)
            if m:
                quick["CPU Temperature (°C)"] = float(m.group(1))
        except Exception:
            pass
    gpu_t = _run(conn, "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -n1")
    try:
        if gpu_t and gpu_t.strip().replace('.', '', 1).isdigit():
            quick["GPU Temperature (°C)"] = float(gpu_t.strip())
    except Exception:
        pass
    return quick


def _get_motherboard(conn: Connection) -> dict:
    res = {}
    vendor = _run(conn, "cat /sys/class/dmi/id/board_vendor 2>/dev/null") or _run(conn, "cat /sys/class/dmi/id/chassis_vendor 2>/dev/null")
    product = _run(conn, "cat /sys/class/dmi/id/board_name 2>/dev/null") or _run(conn, "cat /sys/class/dmi/id/product_name 2>/dev/null")
    bios = _run(conn, "cat /sys/class/dmi/id/bios_version 2>/dev/null") or _run(conn, "cat /sys/class/dmi/id/bios_date 2>/dev/null")
    if vendor:
        res["manufacturer"] = vendor
    if product:
        res["product"] = product
    if bios:
        res["bios_version"] = bios
    return res or {"note": "Motherboard info not available"}


def query_remote(host, user, ip=None):
    target = ip or host
    try:
        with Connection(host=target, user=user, connect_timeout=6) as c:
            data = {}
            data.update({"Host": target, "User": user})
            data["OS Info"] = _get_os_info(c)
            data["CPU Info"] = _get_cpu_info(c)
            data["Memory Info"] = _get_mem_info(c)
            data["GPU Info"] = _get_gpu_info(c)
            data["Temperatures"] = _get_temp_summary(c)
            data["Motherboard"] = _get_motherboard(c)
            return data
    except Exception as e:
        msg = f"SSH connection failed to {target} as {user}: {str(e)}"
        return {"error": msg}
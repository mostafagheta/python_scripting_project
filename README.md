
# Python System Monitor (python-test)

This project is a compact, cross-platform system monitor written in Python. It gathers CPU, GPU, memory, temperature, voltage, power, network and motherboard information using a set of small probe modules and presents them in a modern CustomTkinter GUI.

The codebase is intentionally modular: each piece of hardware or metric lives in `modules/` as a small, testable function. The GUI (`main.py`) imports these modules and prints structured, colorized output for easy reading.

-- Project arc (what this repository contains and why)
 - Purpose: Provide a lightweight desktop monitor that works out-of-the-box on Linux and Windows where possible. Focus points:
	- Collect commonly useful metrics (CPU, Memory, GPU, Temperatures, Voltages, Power, Network).
	- Use best-effort, non-blocking probes: prefer vendor tools (e.g., `nvidia-smi`) when available and fall back to hwmon/sysfs and `psutil`.
	- Keep the GUI simple and readable — monospace output, color tags, and a left-side navigation for quick checks.
	- Make the code modular so you can swap or extend probes for your hardware.

-- Quick start
1. Create a virtual environment (recommended) and install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

2. Optional (system packages) — Linux only: install lm-sensors to expose additional hwmon readings and `python3-tk` if the GUI complains.

Debian/Ubuntu example:
```bash
sudo apt update
sudo apt install lm-sensors python3-tk
sudo sensors-detect   # accept recommended defaults, then modprobe suggested modules or reboot
```

3. Run the app:
```bash
python3 main.py
```

If `nvidia-smi` or other vendor tools are available, the app will use them for better GPU/memory/power readings.

-- Modules and what they do
All modules are under `modules/`. Each module exposes one or a few small functions returning plain Python dicts.

- `modules/cpu_info.py`
	- get_cpu_info(): CPU model, cores, threads, frequency

- `modules/memory_info.py`
	- get_memory_info(): Total RAM (GB), DIMM Type, Frequency, Channel
	- Falls back to `dmidecode` and `lshw` where available; `dmidecode` may require sudo.

- `modules/gpu_info.py`
	- get_gpu_info(): Detects GPUs (prefer `nvidia-smi` for NVIDIA), returns Name, Vendor, Memory, Temperature
	- Improved lspci parsing and hwmon mapping to match temps to the correct GPU device

- `modules/temp_info.py`
	- get_temperatures(): CPU/GPU/RAM/VRM temperatures (best-effort)
	- get_all_hwmon_sensors(): diagnostic helper that lists all `/sys/class/hwmon` labels and values

- `modules/volt_info.py`
	- get_power_info(), get_voltages(), get_power(): Attempt to read voltages and power via `sensors`/hwmon or battery heuristics; voltages from hwmon require kernel drivers.

- `modules/network.py`
	- get_network_rates(): network interface bytes/packets rates

- `modules/os_info.py`
	- get_os_info(): platform, kernel, uptime

- `modules/motherboard_info.py`
	- get_motherboard_info(): manufacturer, product, BIOS version and chipset via `/sys/class/dmi` and fallbacks

- `modules/stress_test.py` and `modules/remote_monitor.py`
	- Small helpers: stress testing and remote monitoring placeholders.

-- Troubleshooting & notes
- Many sensors and voltages are provided by kernel drivers and sysfs (`/sys/class/hwmon`). Tools like `lm-sensors` and `sensors-detect` probe and enable kernel drivers — install them if you want more sensor data.
- `dmidecode` may require sudo; it reads DMI/SMBIOS tables and is the best source for DIMM types/frequencies when available.
- GPU detection: the project prefers `nvidia-smi` for NVIDIA cards (if the NVIDIA driver is installed). For other vendors it falls back to `lspci` and hwmon.
- If a value is `None` in the GUI, it usually means the kernel/hardware/utility didn't expose it on that machine — not a bug in the code. Use `modules.temp_info.get_all_hwmon_sensors()` to inspect raw hwmon information.

-- Developer notes / extension points
- Add additional vendor tools (Intel oneAPI, AMD roc-smi) to improve platform coverage.
- Consider adding a user-configurable mapping UI so the user can map hwmon labels to VRM/RAM in the GUI.
- Long-running probes (e.g., `dmidecode`) should be executed in a background thread or on-demand to keep the GUI responsive.

-- Try it: quick diagnostic commands
From the project root (after activating `.venv`):

```bash
python3 - <<'PY'
import modules.temp_info as t, json
print(json.dumps(t.get_all_hwmon_sensors(), indent=2))
print(t.get_temperatures())
import modules.volt_info as v
print(v.get_voltages())
print(v.get_power())
PY
```

-- License & contribution
This project is provided as-is for learning and small personal monitoring tasks. Feel free to open issues or PRs if you want improvements. If you contribute, add tests for new probe logic and keep probes best-effort and non-blocking.

-- Contact
Open an issue in this repository with logs, outputs from the diagnostic commands, and your OS/distro if you want help mapping missing sensors.

Enjoy!

Quick start

1. Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app:

```bash
python3 main.py
```

Notes
- `dmidecode` may require root to read BIOS/DMI tables. If not available, the module will fall back to sysfs and lspci where possible.
- Some modules are placeholders on certain platforms (voltages/power, motherboard detection on non-Linux).
- If the GUI fails to start, run `python3 main.py` from a terminal to capture tracebacks.

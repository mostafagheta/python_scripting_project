# Professional System Monitor

Simple cross-platform-ish system monitor demo using CustomTkinter. It shows CPU, memory, GPU, temperatures, volt/power placeholders, network rates, OS info, and motherboard information (Linux-focused).

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

# SYSPULSE

> **A `btop`-style terminal system monitor for Windows (and cross-platform) built with Python, `psutil`, and `Rich`.**

![Python](https://img.shields.io/badge/Python-3.9%2B-111111?style=flat-square&logo=python&logoColor=FF4D00)
![License](https://img.shields.io/badge/License-MIT-FF4D00?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-111111?style=flat-square)

**SysPulse** brings the visual telemetry feel of `btop` straight to Windows Command Prompt, PowerShell, and Windows Terminal—with zero C++ build headaches. It tracks live CPU core utilization, rolling sparkline history, RAM/swap usage, drive partitions, network throughput, and active processes, plus one-shot JSON output for scripts.

---

## Why SysPulse?

- **Built for Windows Terminals:** Works out of the box on Windows (alongside Linux and macOS) using prebuilt `psutil` wheels—no C++ compiler required.
- **`btop`-Inspired TUI Layout:** High-contrast dark panels, block progress bars, ASCII sparklines, and live process rankings in your terminal.
- **[01] CPU Telemetry:** Total CPU bar, sparkline load trend, physical/logical core counts, clock speeds, load averages, and per-core readouts.
- **[02] Memory & Swap:** Real-time RAM usage, available memory, sparkline history, and swap monitoring.
- **[03] Network & Storage:** Live download/upload speed (`▼ / ▲`), total RX/TX bytes, and drive/mount utilization bars.
- **[04] Active Processes:** Sortable process table by CPU (`--sort cpu`) or memory (`--sort mem`).
- **JSON Snapshot Mode:** Export a single telemetry snapshot with `syspulse --json` for automation or piping into tools like `jq`.

---

## Installation

### Requirements
- **Python 3.9+** (`pip` included)
- Runtime dependencies (`psutil` and `rich`) install automatically via `pip`.

### Windows (PowerShell or Command Prompt)

```powershell
git clone https://github.com/nirbhontop/syspulse.git
cd syspulse
python -m venv .venv
.venv\Scripts\activate
pip install .
```

### Editable Install (For Active Development)

If you plan to edit the source code and want changes reflected right away without reinstalling every time:

```powershell
pip install -e .
```

### Linux / macOS

```bash
git clone https://github.com/nirbhontop/syspulse.git
cd syspulse
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

---

## Usage

Launch the live interactive dashboard:

```bash
syspulse
```

Press **`Ctrl + C`** to exit back to your terminal.

### CLI Flags

| Flag | Description | Default |
| :--- | :--- | :--- |
| `-r`, `--refresh <sec>` | Refresh interval in seconds (minimum `0.2`) | `1.0` |
| `-s`, `--sort <cpu\|mem>` | Sort top processes by CPU or Memory usage | `cpu` |
| `-n`, `--procs <count>` | Number of top processes to show (`1–50`) | `8` |
| `--once` | Render one frame and exit immediately | `False` |
| `--json` | Print current telemetry as formatted JSON and exit | `False` |
| `-v`, `--version` | Print the installed version and exit | — |

### Examples

```bash
# Refresh every 0.5s and rank processes by memory usage
syspulse -r 0.5 -s mem

# Print a single static snapshot without entering fullscreen mode
syspulse --once

# Export live telemetry as JSON
syspulse --json
```

---

## Project Structure

```text
syspulse/
├── syspulse/
│   ├── __init__.py      # Package version and metadata
│   ├── cli.py           # CLI argument parser and live loop
│   ├── metrics.py       # Cross-platform system metric collectors
│   └── ui.py            # Terminal UI layout, bars, and sparklines
├── tests/
│   └── test_metrics.py  # Unit tests for formatters, metrics, and CLI
├── pyproject.toml       # Package metadata and `syspulse` script entry
├── requirements.txt     # Core dependencies
├── LICENSE              # MIT License
└── README.md            # Project documentation
```

---

## Running Tests

```bash
python -m unittest discover -s tests
```

---

## License

This project is released under the **MIT License**. You are free to use, copy, modify, merge, publish, distribute, and sublicense this software in personal or commercial projects, provided the original copyright notice and permission notice are included. See the [LICENSE](LICENSE) file for the full text.
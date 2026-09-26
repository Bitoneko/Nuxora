# Nuxora

Real-time Linux system monitor and diagnostics TUI.

Nuxora is a terminal-based system monitor designed to provide a detailed, live view of your Linux system in a single interface.

It continuously updates system information while you work, making it easy to monitor CPU, memory, GPU, processes, storage, network activity, temperatures, and other system resources.

## Features

- Real-time system monitoring
- CPU usage and per-core statistics
- Memory and swap usage
- NVIDIA GPU monitoring
- GPU memory and utilization
- Process monitoring
- Disk usage and I/O activity
- Network traffic
- Temperature and hardware sensors
- Live system statistics
- Interactive terminal interface
- Keyboard-driven navigation
- Configurable refresh interval
- Lightweight terminal operation
- AI workload detection
- GPU process monitoring
- Disk analyzer
- Network connection viewer
- Service monitoring
- Container monitoring
- System diagnostics
- Log viewer

## Installation

Clone the repository:

```bash
git clone https://github.com/Bitoneko/Nuxora.git
cd Nuxora
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install Nuxora and its dependencies:

```bash
pip install .
```

## Usage

Start Nuxora from the terminal:

```bash
nuxora
```

Nuxora runs as a live terminal application and continuously updates system information while it is running.

### Keyboard Controls

| Key | Action |
|---|---|
| `Q` | Quit Nuxora |
| `R` | Refresh data |
| `Ctrl+S` | Open settings |

## Requirements

- Linux
- Python 3.10+
- A terminal with Unicode support

For NVIDIA GPU monitoring:

- NVIDIA GPU
- NVIDIA drivers
- NVIDIA Management Library (NVML)

Additional system components may be required for hardware-specific monitoring.

## Project Status

Nuxora is currently in development.

The interface and available features may change as the project evolves.

### © 2026 Bitoneko.
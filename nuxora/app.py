import json
import os
import platform
import subprocess
import time
from pathlib import Path

import psutil
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Footer, Header, Static

from collectors.ai import get_ai_processes
from collectors.audio import get_audio
from collectors.battery import get_battery
from collectors.bluetooth import get_bluetooth
from collectors.containers import get_containers
from collectors.cpu import get_cpu
from collectors.cuda import get_cuda
from collectors.cron import get_crontab, get_timers
from collectors.disks import get_devices, get_disks, get_io
from collectors.filesystem import get_filesystems
from collectors.gpu import get_gpu
from collectors.gpu_processes import get_gpu_processes
from collectors.kernel import get_kernel
from collectors.logs import get_logs
from collectors.memory import get_memory
from collectors.mounts import get_mounts
from collectors.network import get_network
from collectors.ollama import get_ollama
from collectors.packages import get_packages
from collectors.pci import get_pci
from collectors.processes import get_processes
from collectors.processes_tree import get_process_tree
from collectors.pytorch import get_pytorch
from collectors.sensors import get_sensors
from collectors.services import get_services
from collectors.system import get_system
from collectors.usb import get_usb
from collectors.users import get_users
from collectors.virtualization import get_virtualization
from collectors.wifi import get_wifi


class SettingsScreen(ModalScreen):
    CSS = """
    SettingsScreen {
        align: center middle;
        background: $background 80%;
    }

    #settings {
        width: 60%;
        height: 80%;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }

    #settings-title {
        height: 3;
        text-style: bold;
    }

    #checks {
        height: 1fr;
        overflow: auto;
    }

    #buttons {
        height: 3;
        align: right middle;
    }

    Button {
        margin-left: 1;
    }
    """

    def __init__(self, app):
        super().__init__()
        self.main_app = app

    def compose(self):
        with Vertical(id="settings"):
            yield Static("NUXORA DISPLAY SETTINGS", id="settings-title")

            with ScrollableContainer(id="checks"):
                for key, name in self.main_app.collectors:
                    yield Checkbox(
                        name,
                        value=self.main_app.enabled(key),
                        id=f"check-{key}",
                    )

            with Horizontal(id="buttons"):
                yield Button("Show All", id="show-all")
                yield Button("Hide All", id="hide-all")
                yield Button("Apply", variant="primary", id="apply")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event):
        button_id = event.button.id

        if button_id == "cancel":
            self.dismiss()
            return

        if button_id == "show-all":
            for key, _ in self.main_app.collectors:
                self.query_one(
                    f"#check-{key}",
                    Checkbox,
                ).value = True
            return

        if button_id == "hide-all":
            for key, _ in self.main_app.collectors:
                self.query_one(
                    f"#check-{key}",
                    Checkbox,
                ).value = False
            return

        if button_id != "apply":
            return

        for key, _ in self.main_app.collectors:
            value = self.query_one(
                f"#check-{key}",
                Checkbox,
            ).value

            self.main_app.collector_visibility[key] = value
            self.main_app.set_panel_visible(key, value)

        self.main_app.save_visibility()
        self.main_app.refresh_all()
        self.dismiss()


class Nuxora(App):
    TITLE = "Nuxora"
    SUB_TITLE = "Linux System Monitor"

    CSS = """
    Screen {
        background: $background;
    }

    #dashboard {
        height: 1fr;
        padding: 0 1;
        overflow: auto;
    }

    #panels {
        width: 100%;
        height: auto;
    }

    .panel {
        width: 100%;
        height: auto;
        min-height: 7;
        max-height: 13;
        border: solid $accent;
        padding: 0 1;
    }

    .panel.maximized {
        height: 40;
        min-height: 20;
        max-height: 40;
    }

    .title {
        width: 1fr;
        height: 2;
        text-style: bold;
        color: $accent;
    }

    .content {
        width: 1fr;
        height: auto;
        max-height: 8;
        overflow: hidden;
    }

    .panel.maximized .content {
        height: 30;
        max-height: 30;
        overflow: auto;
    }

    .panel-button {
        width: 100%;
        height: 3;
        margin-top: 1;
    }

    Static {
        width: 1fr;
        height: auto;
    }
    """

    collectors = [
        ("system", "System"),
        ("cpu", "CPU"),
        ("memory", "Memory"),
        ("gpu", "GPU"),
        ("disk", "Disk"),
        ("network", "Network"),
        ("processes", "Processes"),
        ("sensors", "Sensors"),
        ("services", "Services"),
        ("filesystem", "Filesystem"),
        ("usb", "USB"),
        ("pci", "PCI"),
        ("battery", "Battery"),
        ("audio", "Audio"),
        ("bluetooth", "Bluetooth"),
        ("wifi", "Wi-Fi"),
        ("users", "Users"),
        ("logs", "Logs"),
        ("kernel", "Kernel"),
        ("process_tree", "Process Tree"),
        ("containers", "Containers"),
        ("virtualization", "Virtualization"),
        ("packages", "Packages"),
        ("mounts", "Mounts"),
        ("cron", "Cron / Timers"),
        ("gpu_processes", "GPU Processes"),
        ("ai", "AI Processes"),
        ("ollama", "Ollama"),
        ("cuda", "CUDA"),
        ("pytorch", "PyTorch"),
    ]

    fast = {
        "system",
        "cpu",
        "memory",
        "gpu",
        "network",
    }

    medium = {
        "disk",
        "processes",
        "sensors",
        "battery",
        "wifi",
        "gpu_processes",
        "ai",
        "pytorch",
    }

    slow = {
        "services",
        "filesystem",
        "usb",
        "pci",
        "audio",
        "bluetooth",
        "users",
        "logs",
        "kernel",
        "process_tree",
        "containers",
        "virtualization",
        "packages",
        "mounts",
        "cron",
        "ollama",
        "cuda",
    }

    def __init__(self):
        super().__init__()

        self.config_dir = (
            Path.home() / ".config" / "nuxora"
        )

        self.visibility_file = (
            self.config_dir / "visibility.json"
        )

        self.theme_file = (
            self.config_dir / "theme.json"
        )

        self.collector_visibility = (
            self.load_visibility()
        )

        self.collector_visibility = {
            key: self.collector_visibility.get(key, True)
            for key, _ in self.collectors
        }

        self.jobs = {
            "system": self.collect_system,
            "cpu": self.collect_cpu,
            "memory": self.collect_memory,
            "gpu": self.collect_gpu,
            "network": self.collect_network,
            "disk": self.collect_disk,
            "processes": self.collect_processes,
            "sensors": self.collect_sensors,
            "battery": self.collect_battery,
            "wifi": self.collect_wifi,
            "gpu_processes": self.collect_gpu_processes,
            "ai": self.collect_ai,
            "pytorch": self.collect_pytorch,
            "services": self.collect_services,
            "filesystem": self.collect_filesystem,
            "usb": self.collect_usb,
            "pci": self.collect_pci,
            "audio": self.collect_audio,
            "bluetooth": self.collect_bluetooth,
            "users": self.collect_users,
            "logs": self.collect_logs,
            "kernel": self.collect_kernel,
            "process_tree": self.collect_process_tree,
            "containers": self.collect_containers,
            "virtualization": self.collect_virtualization,
            "packages": self.collect_packages,
            "mounts": self.collect_mounts,
            "cron": self.collect_cron,
            "ollama": self.collect_ollama,
            "cuda": self.collect_cuda,
        }

        self.running = set()

        self.last_network = None
        self.last_disk = None

    def compose(self) -> ComposeResult:
        yield Header()

        with ScrollableContainer(id="dashboard"):
            with Vertical(id="panels"):
                for key, name in self.collectors:
                    yield Vertical(
                        Static(
                            name.upper(),
                            classes="title",
                        ),
                        Static(
                            "Waiting...",
                            id=f"panel-{key}",
                            classes="content",
                        ),
                        Button(
                            "Maximize",
                            id=f"maximize-{key}",
                            classes="panel-button",
                        ),
                        classes="panel",
                        id=f"box-{key}",
                    )

        yield Footer()

    def on_mount(self):
        self.set_interval(
            1,
            self.refresh_fast,
        )

        self.set_interval(
            3,
            self.refresh_medium,
        )

        self.set_interval(
            10,
            self.refresh_slow,
        )

        self.refresh_all()

    def action_settings(self):
        self.push_screen(
            SettingsScreen(self)
        )

    def action_quit(self):
        self.save_visibility()
        self.save_theme()
        self.exit()

    def on_button_pressed(self, event):
        button_id = event.button.id

        if not button_id:
            return

        if button_id.startswith("maximize-"):
            key = button_id.removeprefix(
                "maximize-"
            )

            self.toggle_panel(key)

    def toggle_panel(self, key):
        try:
            panel = self.query_one(
                f"#box-{key}",
                Vertical,
            )

            button = self.query_one(
                f"#maximize-{key}",
                Button,
            )

            if "maximized" in panel.classes:
                panel.remove_class("maximized")
                button.label = "Maximize"
            else:
                panel.add_class("maximized")
                button.label = "Minimize"

        except Exception:
            pass

    def enabled(self, key):
        return self.collector_visibility.get(
            key,
            True,
        )

    def set_panel_visible(self, key, visible):
        try:
            panel = self.query_one(
                f"#box-{key}",
                Vertical,
            )

            if visible:
                panel.display = True
            else:
                panel.display = False

        except Exception:
            pass

    def set(self, key, text):
        try:
            widget = self.query_one(
                f"#panel-{key}",
                Static,
            )

            widget.update(text)

        except Exception:
            pass

    def load_visibility(self):
        try:
            if self.visibility_file.exists():
                with self.visibility_file.open(
                    "r",
                    encoding="utf-8",
                ) as f:
                    data = json.load(f)

                if isinstance(data, dict):
                    return data

        except Exception:
            pass

        return {}

    def save_visibility(self):
        try:
            self.config_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            with self.visibility_file.open(
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(
                    self.collector_visibility,
                    f,
                    indent=2,
                )

        except Exception:
            pass

    def load_theme(self):
        try:
            if self.theme_file.exists():
                with self.theme_file.open(
                    "r",
                    encoding="utf-8",
                ) as f:
                    data = json.load(f)

                if isinstance(data, dict):
                    return data.get("theme")

        except Exception:
            pass

        return None

    def save_theme(self):
        try:
            self.config_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            theme = getattr(
                self,
                "theme",
                None,
            )

            if theme:
                with self.theme_file.open(
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(
                        {"theme": theme},
                        f,
                        indent=2,
                    )

        except Exception:
            pass

    def watch_theme(self, theme):
        self.save_theme()

    def refresh_all(self):
        self.refresh_fast()
        self.refresh_medium()
        self.refresh_slow()

    def refresh_fast(self):
        self.run_group(self.fast)

    def refresh_medium(self):
        self.run_group(self.medium)

    def refresh_slow(self):
        self.run_group(self.slow)

    def run_group(self, group):
        for key in group:
            if self.enabled(key):
                self.run_collector(key)

    def run_collector(self, key):
        if key in self.running:
            return

        if key not in self.jobs:
            return

        self.running.add(key)

        self.run_worker(
            lambda: self.worker(key),
            thread=True,
            exclusive=False,
        )

    def worker(self, key):
        try:
            result = self.jobs[key]()

            self.call_from_thread(
                self.finished,
                key,
                result,
                None,
            )

        except Exception as e:
            self.call_from_thread(
                self.finished,
                key,
                None,
                f"{type(e).__name__}: {e}",
            )

    def finished(self, key, result, error):
        self.running.discard(key)

        if error:
            self.set(
                key,
                f"Collector error: {error}",
            )
            return

        if result is not None:
            self.set(
                key,
                result,
            )

    @staticmethod
    def bar(value, width=18):
        value = max(
            0,
            min(
                100,
                float(value),
            ),
        )

        n = int(
            width * value / 100
        )

        return (
            "█" * n
            + "░" * (width - n)
        )

    @staticmethod
    def bytes(value):
        value = float(value)

        for unit in (
            "B",
            "KB",
            "MB",
            "GB",
            "TB",
        ):
            if abs(value) < 1024:
                return f"{value:.1f} {unit}"

            value /= 1024

        return f"{value:.1f} PB"

    @staticmethod
    def seconds(value):
        if value is None or value < 0:
            return "Unknown"

        return time.strftime(
            "%H:%M:%S",
            time.gmtime(value),
        )

    def collect_system(self):
        try:
            data = get_system()

            return "\n".join(
                [
                    f"OS: {data.get('os', 'Unknown')}",
                    f"Kernel: {data.get('kernel', platform.release())}",
                    f"Machine: {data.get('machine', platform.machine())}",
                    f"Host: {data.get('hostname', platform.node())}",
                    f"Uptime: {self.seconds(data.get('uptime'))}",
                    f"Time: {data.get('time', time.strftime('%H:%M:%S'))}",
                    f"Users: {data.get('users', 'Unknown')}",
                    f"Boot: {data.get('boot', 'Unknown')}",
                    f"Battery: {data.get('battery', 'Unknown')}",
                    f"Charging: {data.get('charging', 'Unknown')}",
                ]
            )

        except Exception:
            return self.basic_system()

    def basic_system(self):
        uptime = (
            time.time()
            - psutil.boot_time()
        )

        return "\n".join(
            [
                f"OS: {platform.system()} {platform.release()}",
                f"Kernel: {platform.release()}",
                f"Machine: {platform.machine()}",
                f"Host: {platform.node()}",
                f"Uptime: {self.seconds(uptime)}",
                f"Time: {time.strftime('%H:%M:%S')}",
                f"Users: {len(psutil.users())}",
                f"Boot: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(psutil.boot_time()))}",
            ]
        )

    def collect_cpu(self):
        try:
            data = get_cpu()

            if isinstance(data, str):
                return data

            if not isinstance(data, dict):
                return str(data)

            lines = [
                f"Usage: {data.get('usage', data.get('percent', 0))}%",
                f"Cores: {data.get('cores', psutil.cpu_count(logical=True))}",
                f"Frequency: {data.get('frequency', 'Unknown')}",
            ]

            per_cpu = data.get("per_cpu")

            if per_cpu:
                lines.append("")
                lines.append("Per-core:")

                for i, value in enumerate(per_cpu):
                    lines.append(
                        f"{i:02d} "
                        f"{self.bar(value, 12)} "
                        f"{value:.1f}%"
                    )

            load = data.get("load")

            if load:
                lines.append("")
                lines.append(
                    f"Load: {load}"
                )

            return "\n".join(lines)

        except Exception as e:
            return f"CPU error: {e}"

    def collect_memory(self):
        try:
            data = get_memory()

            if isinstance(data, str):
                return data

            if not isinstance(data, dict):
                return str(data)

            percent = data.get(
                "percent",
                psutil.virtual_memory().percent,
            )

            lines = [
                f"RAM: {self.bytes(data.get('total', 0))}",
                f"Used: {self.bytes(data.get('used', 0))}",
                f"Usage: {percent:.1f}%",
                self.bar(percent),
                f"Available: {self.bytes(data.get('available', 0))}",
                f"Cached: {self.bytes(data.get('cached', 0))}",
                f"Buffers: {self.bytes(data.get('buffers', 0))}",
                f"Shared: {self.bytes(data.get('shared', 0))}",
            ]

            swap = data.get("swap")

            if isinstance(swap, dict):
                lines.extend(
                    [
                        "",
                        "Swap:",
                        f"Total: {self.bytes(swap.get('total', 0))}",
                        f"Used: {self.bytes(swap.get('used', 0))}",
                        f"Usage: {swap.get('percent', 0):.1f}%",
                    ]
                )

            return "\n".join(lines)

        except Exception as e:
            return f"Memory error: {e}"

    def collect_gpu(self):
        try:
            data = get_gpu()

            if isinstance(data, str):
                return data

            if isinstance(data, list):
                lines = []

                for gpu in data:
                    if isinstance(gpu, dict):
                        name = gpu.get(
                            "name",
                            "GPU",
                        )

                        usage = gpu.get(
                            "utilization",
                            gpu.get("gpu", 0),
                        )

                        lines.extend(
                            [
                                str(name),
                                f"GPU: {usage}%",
                                self.bar(usage),
                                f"VRAM: {self.bytes(gpu.get('memory_used', 0))} / {self.bytes(gpu.get('memory_total', 0))}",
                                f"Temperature: {gpu.get('temperature', 'Unknown')}°C",
                                f"Power: {gpu.get('power', 'Unknown')}",
                                f"Clock: {gpu.get('clock', 'Unknown')}",
                                "",
                            ]
                        )

                return "\n".join(lines).rstrip()

            return str(data)

        except Exception as e:
            return f"GPU error: {e}"

    def collect_network(self):
        try:
            data = get_network()

            if isinstance(data, str):
                return data

            if not isinstance(data, dict):
                return str(data)

            lines = []

            if "download" in data:
                lines.append(
                    f"Download: {self.bytes(data['download'])}/s"
                )

            if "upload" in data:
                lines.append(
                    f"Upload: {self.bytes(data['upload'])}/s"
                )

            if "rx" in data:
                lines.append(
                    f"RX total: {self.bytes(data['rx'])}"
                )

            if "tx" in data:
                lines.append(
                    f"TX total: {self.bytes(data['tx'])}"
                )

            if "packets_rx" in data:
                lines.append(
                    f"Packets RX: {data['packets_rx']}"
                )

            if "packets_tx" in data:
                lines.append(
                    f"Packets TX: {data['packets_tx']}"
                )

            if "errors" in data:
                lines.append(
                    f"Errors: {data['errors']}"
                )

            interfaces = data.get("interfaces")

            if interfaces:
                lines.append("")
                lines.append("Interfaces:")

                if isinstance(interfaces, dict):
                    for name, info in interfaces.items():
                        lines.append(
                            f"{name}: {info}"
                        )
                else:
                    for item in interfaces:
                        lines.append(str(item))

            connections = data.get("connections")

            if connections is not None:
                lines.append("")
                lines.append(
                    f"Connections: {connections}"
                )

            return "\n".join(lines) or str(data)

        except Exception as e:
            return f"Network error: {e}"

    def collect_disk(self):
        try:
            parts = get_disks()
            io = get_io()
            devices = get_devices()

            lines = []

            if parts:
                lines.append("Partitions:")

                if isinstance(parts, dict):
                    for name, value in parts.items():
                        lines.append(
                            f"{name}: {value}"
                        )
                else:
                    for item in parts:
                        lines.append(str(item))

            if io:
                lines.append("")
                lines.append("I/O:")

                if isinstance(io, dict):
                    for name, value in io.items():
                        lines.append(
                            f"{name}: {value}"
                        )
                else:
                    lines.extend(
                        str(item)
                        for item in io
                    )

            if devices:
                lines.append("")
                lines.append("Block devices:")

                if isinstance(devices, dict):
                    for name, value in devices.items():
                        lines.append(
                            f"{name}: {value}"
                        )
                else:
                    lines.extend(
                        str(item)
                        for item in devices
                    )

            return "\n".join(lines) or "No disk data"

        except Exception as e:
            return f"Disk error: {e}"

    def collect_processes(self):
        try:
            data = get_processes()

            if isinstance(data, str):
                return data

            if isinstance(data, dict):
                data = data.get(
                    "processes",
                    data,
                )

            if not isinstance(data, list):
                return str(data)

            lines = [
                f"{'PID':>7} "
                f"{'CPU':>6} "
                f"{'RAM':>6} "
                f"{'NAME'}"
            ]

            for item in data[:25]:
                if isinstance(item, dict):
                    lines.append(
                        f"{str(item.get('pid', '')):>7} "
                        f"{str(item.get('cpu', item.get('cpu_percent', ''))):>6} "
                        f"{str(item.get('ram', item.get('memory_percent', ''))):>6} "
                        f"{item.get('name', item.get('process', ''))}"
                    )
                else:
                    lines.append(str(item))

            return "\n".join(lines)

        except Exception as e:
            return f"Processes error: {e}"

    def generic_collector(self, fn, label):
        try:
            data = fn()

            if isinstance(data, str):
                return data

            if isinstance(data, dict):
                lines = []

                for key, value in data.items():
                    lines.append(
                        f"{key}: {value}"
                    )

                return "\n".join(lines)

            if isinstance(data, list):
                return "\n".join(
                    str(item)
                    for item in data
                )

            return str(data)

        except Exception as e:
            return f"{label} error: {e}"

    def collect_sensors(self):
        return self.generic_collector(
            get_sensors,
            "Sensors",
        )

    def collect_services(self):
        data = self.generic_collector(
            get_services,
            "Services",
        )
        return data[:10000]

    def collect_filesystem(self):
        return self.generic_collector(
            get_filesystems,
            "Filesystem",
        )

    def collect_usb(self):
        return self.generic_collector(
            get_usb,
            "USB",
        )

    def collect_pci(self):
        return self.generic_collector(
            get_pci,
            "PCI",
        )

    def collect_battery(self):
        return self.generic_collector(
            get_battery,
            "Battery",
        )

    def collect_audio(self):
        return self.generic_collector(
            get_audio,
            "Audio",
        )

    def collect_bluetooth(self):
        return self.generic_collector(
            get_bluetooth,
            "Bluetooth",
        )

    def collect_wifi(self):
        return self.generic_collector(
            get_wifi,
            "Wi-Fi",
        )

    def collect_users(self):
        return self.generic_collector(
            get_users,
            "Users",
        )

    def collect_logs(self):
        data = self.generic_collector(
            get_logs,
            "Logs",
        )
        return data[:12000]

    def collect_kernel(self):
        return self.generic_collector(
            get_kernel,
            "Kernel",
        )

    def collect_process_tree(self):
        data = self.generic_collector(
            get_process_tree,
            "Process Tree",
        )
        return data[:12000]

    def collect_containers(self):
        return self.generic_collector(
            get_containers,
            "Containers",
        )

    def collect_virtualization(self):
        return self.generic_collector(
            get_virtualization,
            "Virtualization",
        )

    def collect_packages(self):
        data = self.generic_collector(
            get_packages,
            "Packages",
        )
        return data[:12000]

    def collect_mounts(self):
        return self.generic_collector(
            get_mounts,
            "Mounts",
        )

    def collect_cron(self):
        try:
            cron = get_crontab()
            timers = get_timers()

            return (
                "Crontab:\n"
                + str(cron)
                + "\n\nTimers:\n"
                + str(timers)
            )

        except Exception as e:
            return f"Cron error: {e}"

    def collect_gpu_processes(self):
        return self.generic_collector(
            get_gpu_processes,
            "GPU Processes",
        )

    def collect_ai(self):
        return self.generic_collector(
            get_ai_processes,
            "AI Processes",
        )

    def collect_ollama(self):
        return self.generic_collector(
            get_ollama,
            "Ollama",
        )

    def collect_cuda(self):
        return self.generic_collector(
            get_cuda,
            "CUDA",
        )

    def collect_pytorch(self):
        return self.generic_collector(
            get_pytorch,
            "PyTorch",
        )


if __name__ == "__main__":
    Nuxora().run()

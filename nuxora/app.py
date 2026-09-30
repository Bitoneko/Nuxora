import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from textual.app import App, ComposeResult
from textual.binding import Binding
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
            yield Static(
                "NUXORA DISPLAY SETTINGS",
                id="settings-title",
            )

            with ScrollableContainer(id="checks"):
                for key, name in self.main_app.collectors:
                    yield Checkbox(
                        name,
                        value=self.main_app.enabled(key),
                        id=f"check-{key}",
                    )

            with Horizontal(id="buttons"):
                yield Button(
                    "Show All",
                    id="show-all",
                )
                yield Button(
                    "Hide All",
                    id="hide-all",
                )
                yield Button(
                    "Apply",
                    variant="primary",
                    id="apply",
                )
                yield Button(
                    "Cancel",
                    id="cancel",
                )

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

            self.main_app.set_panel_visible(
                key,
                value,
            )

        self.main_app.save_visibility()
        self.main_app.refresh_all()
        self.dismiss()


class Nuxora(App):
    TITLE = "Nuxora"

    inherit_bindings = False

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
        height: 16;
        min-height: 16;
        max-height: 16;
        border: solid $accent;
        padding: 0 1;
    }

    .panel.maximized {
        width: 100%;
        height: 40;
        min-height: 40;
        max-height: 40;
    }

    .panel-title {
        width: 1fr;
        height: 2;
        min-height: 2;
        max-height: 2;
        text-style: bold;
        color: $accent;
    }

    .content {
        width: 1fr;
        height: 8;
        min-height: 8;
        max-height: 8;
        overflow: hidden;
    }

    .panel.maximized .content {
        width: 1fr;
        height: 30;
        min-height: 30;
        max-height: 30;
        overflow: auto;
    }

    .panel-button {
        width: 100%;
        height: 3;
        min-height: 3;
        max-height: 3;
        margin-top: 1;
    }

    Static {
        width: 1fr;
        height: auto;
    }
    """

    BINDINGS = [
        Binding(
            "q",
            "quit",
            "Quit",
        ),
        Binding(
            "r",
            "refresh_all",
            "Refresh",
        ),
        Binding(
            "ctrl+s",
            "settings",
            "Settings",
        ),
        Binding(
            "ctrl+c",
            "copy",
            "Copy",
        ),
    ]

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
        "battery",
        "wifi",
        "sensors",
    }

    slow = {
        "processes",
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
        "gpu_processes",
        "ai",
        "ollama",
        "cuda",
        "pytorch",
    }

    def __init__(self):
        super().__init__()

        base = os.path.expanduser(
            "~/.config/nuxora"
        )

        self.visibility_path = (
            f"{base}/visibility.json"
        )

        self.theme_path = (
            f"{base}/theme.json"
        )

        self.collector_visibility = (
            self.load_visibility()
        )

        self.running = set()
        self._cache = {}
        self._cache_time = {}
        self._collector_lock = threading.Lock()

        self.net = None
        self.net_time = time.monotonic()

        self.executor = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="nuxora-collector"
        )

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

        self._is_shutdown = False

    def compose(self) -> ComposeResult:
        yield Header()

        with ScrollableContainer(id="dashboard"):
            with Vertical(id="panels"):
                for key, name in self.collectors:
                    yield Vertical(
                        Static(
                            name.upper(),
                            classes="panel-title",
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
        self.load_theme()

        for key, _ in self.collectors:
            self.set_panel_visible(
                key,
                self.enabled(key),
            )

        self.refresh_all()

        self.set_interval(
            0.5,
            self.update_fast,
        )

        self.set_interval(
            1,
            self.update_medium,
        )

        self.set_interval(
            5,
            self.update_slow,
        )

    def on_unmount(self):
        self._is_shutdown = True
        self.executor.shutdown(wait=False)

    def action_quit(self):
        self._is_shutdown = True
        self.executor.shutdown(wait=False)
        self.save_theme()
        self.save_visibility()
        self.exit()

    def action_refresh_all(self):
        self.refresh_all()

    def action_settings(self):
        self.push_screen(
            SettingsScreen(self)
        )

    def action_copy(self):
        self.screen.action_copy_text()

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

            if panel.has_class("maximized"):
                panel.remove_class("maximized")
                button.label = "Maximize"
            else:
                panel.add_class("maximized")
                button.label = "Minimize"

        except Exception:
            pass

    def refresh_all(self):
        self.update_fast()
        self.update_medium()
        self.update_slow()

    def update_fast(self):
        self.run_group(self.fast)

    def update_medium(self):
        self.run_group(self.medium)

    def update_slow(self):
        self.run_group(self.slow)

    def run_group(self, group):
        for key in group:
            if self.enabled(key):
                self.run_collector(key)

    def run_collector(self, key):
        now = time.monotonic()

        cache_ttl = self._get_cache_ttl(key)
        if cache_ttl > 0 and key in self._cache_time:
            if (now - self._cache_time[key]) < cache_ttl:
                return

        with self._collector_lock:
            if key in self.running:
                return
            self.running.add(key)

        def worker_wrapper():
            if self._is_shutdown:
                return

            try:
                result = self.jobs[key]()
                self.call_from_thread(
                    self._finished,
                    key,
                    result,
                    None,
                )
            except Exception as e:
                self.call_from_thread(
                    self._finished,
                    key,
                    None,
                    f"{type(e).__name__}: {e}",
                )

        self.executor.submit(worker_wrapper)

    def _finished(self, key, result, error):
        with self._collector_lock:
            self.running.discard(key)

        if error:
            self.set(
                key,
                f"Collector error: {error}",
            )
        elif result is not None:
            self._cache[key] = result
            self._cache_time[key] = time.monotonic()
            self.set(
                key,
                result,
            )

    def _get_cache_ttl(self, key):
        cache_ttl_map = {
            "cpu": 0.25,
            "memory": 0.5,
            "gpu": 0.5,
            "network": 0.5,
            "system": 1.0,
            "disk": 1.0,
            "battery": 1.0,
            "wifi": 1.0,
            "sensors": 1.0,
            "processes": 2.0,
            "gpu_processes": 2.0,
            "ai": 2.0,
            "pytorch": 2.0,
            "services": 5.0,
            "filesystem": 5.0,
            "containers": 5.0,
            "process_tree": 3.0,
            "packages": 10.0,
            "logs": 3.0,
            "kernel": 10.0,
            "ollama": 3.0,
            "cuda": 3.0,
        }
        return cache_ttl_map.get(key, 0)

    def enabled(self, key):
        return self.collector_visibility.get(
            key,
            True,
        )

    def set_panel_visible(self, key, visible):
        try:
            self.query_one(
                f"#box-{key}",
                Vertical,
            ).display = visible
        except Exception:
            pass

    def set(self, key, value):
        try:
            self.query_one(
                f"#panel-{key}",
                Static,
            ).update(str(value))
        except Exception:
            pass

    def load_visibility(self):
        result = {
            key: True
            for key, _ in self.collectors
        }

        try:
            with open(
                self.visibility_path,
                encoding="utf-8",
            ) as f:
                data = json.load(f)

            if isinstance(data, dict):
                result.update(
                    {
                        k: bool(v)
                        for k, v in data.items()
                        if k in result
                    }
                )

        except Exception:
            pass

        return result

    def save_visibility(self):
        try:
            os.makedirs(
                os.path.dirname(
                    self.visibility_path
                ),
                exist_ok=True,
            )

            with open(
                self.visibility_path,
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
            with open(
                self.theme_path,
                encoding="utf-8",
            ) as f:
                theme = json.load(f).get("theme")

            if theme in self.available_themes:
                self.theme = theme

        except Exception:
            pass

    def save_theme(self):
        try:
            os.makedirs(
                os.path.dirname(
                    self.theme_path
                ),
                exist_ok=True,
            )

            with open(
                self.theme_path,
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(
                    {"theme": self.theme},
                    f,
                )

        except Exception:
            pass

    def watch_theme(self, theme):
        self.save_theme()

    def collect_system(self):
        s = get_system()

        b = (
            f"\nBattery   {s['battery']:.0f}%"
            + (
                " Charging"
                if s.get("charging")
                else ""
            )
            if s.get("battery") is not None
            else ""
        )

        return (
            f"OS        {s['os']}\n"
            f"Kernel    {s['kernel']}\n"
            f"Machine   {s['machine']}\n"
            f"Host      {s['host']}\n"
            f"Uptime    {s['uptime']}\n"
            f"Time      {s['time']}\n"
            f"Users     {s['users']}\n"
            f"Boot      {s['boot']}{b}"
        )

    def collect_cpu(self):
        c = get_cpu()
        f = c["frequency"]

        lines = [
            f"Total     {c['total']:5.1f}%",
            f"Cores     {c['count']} "
            f"({c['physical']} physical)",
        ]

        if f:
            lines += [
                f"Clock     {f.current:5.0f} MHz",
                f"Max       {f.max:5.0f} MHz",
            ]

        lines += [
            "",
            *[
                f"{i:02d} "
                f"{self.bar(v, 20)} "
                f"{v:5.1f}%"
                for i, v in enumerate(c["cores"])
            ],
            "",
            f"Load      "
            f"{c['load'][0]:.2f} "
            f"{c['load'][1]:.2f} "
            f"{c['load'][2]:.2f}",
        ]

        return "\n".join(lines)

    def collect_memory(self):
        m = get_memory()
        r, s = m["ram"], m["swap"]

        return (
            f"RAM       "
            f"{self.bytes(r.used)} / "
            f"{self.bytes(r.total)}\n"
            f"Usage     {r.percent:5.1f}%\n"
            f"{self.bar(r.percent)}\n\n"
            f"Available "
            f"{self.bytes(r.available)}\n"
            f"Cached    "
            f"{self.bytes(getattr(r, 'cached', 0))}\n"
            f"Buffers   "
            f"{self.bytes(getattr(r, 'buffers', 0))}\n"
            f"Shared    "
            f"{self.bytes(getattr(r, 'shared', 0))}\n\n"
            f"SWAP      "
            f"{self.bytes(s.used)} / "
            f"{self.bytes(s.total)}\n"
            f"Usage     {s.percent:5.1f}%\n"
            f"{self.bar(s.percent)}"
        )

    def collect_gpu(self):
        gpus = get_gpu()

        if not gpus:
            return "NVIDIA GPU unavailable.
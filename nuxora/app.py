import json
import os
import time

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
        min-height: 9;
        max-height: 14;
        border: solid $accent;
        padding: 0 1;
    }

    .panel.maximized {
        height: 40;
        min-height: 20;
        max-height: 40;
    }

    .panel-title {
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

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_all", "Refresh"),
        ("ctrl+s", "settings", "Settings"),
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

        self.net = None
        self.net_time = time.monotonic()

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
            1,
            self.update_fast,
        )

        self.set_interval(
            3,
            self.update_medium,
        )

        self.set_interval(
            10,
            self.update_slow,
        )

    def action_quit(self):
        self.save_theme()
        self.save_visibility()
        self.exit()

    def action_refresh_all(self):
        self.refresh_all()

    def action_settings(self):
        self.push_screen(
            SettingsScreen(self)
        )

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
        if key in self.running:
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
        elif result is not None:
            self.set(
                key,
                result,
            )

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
            return "NVIDIA GPU unavailable."

        lines = []

        for i, g in enumerate(gpus):
            u = (
                g["vram_used"]
                / g["vram_total"]
                * 100
                if g["vram_total"]
                else 0
            )

            lines += [
                g["name"],
                f"GPU       {g['gpu']:5.1f}%",
                f"VRAM      "
                f"{self.bytes(g['vram_used'])} / "
                f"{self.bytes(g['vram_total'])}",
                f"Usage     {u:5.1f}%\n"
                f"{self.bar(u)}",
                f"Temp      "
                f"{g.get('temp', 0)}°C",
                f"Power     "
                f"{g.get('power', 0):.1f} W",
                f"Clock     "
                f"{g.get('clock', 0)} MHz",
                f"Mem Clock "
                f"{g.get('memclock', 0)} MHz",
            ]

            if g.get("fan") is not None:
                lines.append(
                    f"Fan       {g['fan']}%"
                )

            if i < len(gpus) - 1:
                lines.append("")

        return "\n".join(lines)

    def collect_network(self):
        n = get_network()
        total = n["total"]
        now = time.monotonic()

        if self.net is None:
            self.net = total
            self.net_time = now

        dt = max(
            now - self.net_time,
            0.001,
        )

        rx = (
            total.bytes_recv
            - self.net.bytes_recv
        ) / dt

        tx = (
            total.bytes_sent
            - self.net.bytes_sent
        ) / dt

        self.net = total
        self.net_time = now

        lines = [
            f"Download   "
            f"{self.bytes(rx)}/s",
            f"Upload     "
            f"{self.bytes(tx)}/s",
            "",
            f"Total RX   "
            f"{self.bytes(total.bytes_recv)}",
            f"Total TX   "
            f"{self.bytes(total.bytes_sent)}",
            "",
            f"Packets RX "
            f"{total.packets_recv:,}",
            f"Packets TX "
            f"{total.packets_sent:,}",
            f"Errors RX  "
            f"{total.errin:,}",
            f"Errors TX  "
            f"{total.errout:,}",
            "",
        ]

        lines += [
            f"{name[:12]:12} "
            f"↓{self.bytes(i.bytes_recv)} "
            f"↑{self.bytes(i.bytes_sent)}"
            for name, i in n["interfaces"].items()
        ]

        return "\n".join(
            lines
            + [
                "",
                f"Connections "
                f"{len(n['connections'])}",
            ]
        )

    def collect_disk(self):
        lines = []

        for d in get_disks():
            lines += [
                d["device"],
                d["mount"],
                f"{self.bar(d['percent'])} "
                f"{d['percent']:5.1f}%",
                f"Used      "
                f"{self.bytes(d['used'])}",
                f"Free      "
                f"{self.bytes(d['free'])}",
                f"Total     "
                f"{self.bytes(d['total'])}",
                f"Type      "
                f"{d['fstype']}",
                "",
            ]

        io = get_io()

        if io:
            lines += [
                f"Read      "
                f"{self.bytes(io.read_bytes)}",
                f"Write     "
                f"{self.bytes(io.write_bytes)}",
            ]

        devices = get_devices()

        if devices:
            lines.append(
                "\nBLOCK DEVICES"
            )

            lines += [
                f"{d.get('path', d.get('name', '?')):16} "
                f"{d.get('size', '?'):>9} "
                f"{d.get('type', '?'):6} "
                f"{d.get('model') or ''}"
                for d in devices
            ]

        return "\n".join(lines) or "No disks."

    def collect_processes(self):
        p = get_processes()[:25]

        return "\n".join(
            [
                "PID       PROCESS                       "
                "CPU      RAM       MEMORY       STATUS",
                *[
                    f"{x['pid']:<9}"
                    f"{x['name'][:28]:<29}"
                    f"{x['cpu']:>5.1f}%   "
                    f"{x['ram']:>5.1f}%   "
                    f"{self.bytes(x['memory']):>10}   "
                    f"{x['status']}"
                    for x in p
                ],
            ]
        )

    def collect_sensors(self):
        s = get_sensors()
        lines = []

        for chip, items in s["temperatures"].items():
            lines.append(chip)

            for x in items:
                h = (
                    f" high "
                    f"{x['high']:.1f}°C"
                    if x["high"]
                    else ""
                )

                lines.append(
                    f"  "
                    f"{x['label'] or '?':20} "
                    f"{x['current']:6.1f}°C"
                    f"{h}"
                )

        for items in s["fans"].values():
            for x in items:
                lines.append(
                    f"  FAN "
                    f"{x['label'] or '?':16} "
                    f"{x['current']:6.0f} RPM"
                )

        return (
            "\n".join(lines)
            or "No sensors found."
        )

    def collect_services(self):
        return "\n".join(
            f"{x['name']:<40} "
            f"{x['active']:<8} "
            f"{x['sub']:<10} "
            f"{x['description']}"
            for x in get_services()[:100]
        ) or "No services found."

    def collect_filesystem(self):
        return "\n".join(
            f"{x['mount']:<25} "
            f"{x['fstype']:<8} "
            f"{self.bar(x['percent'], 16)} "
            f"{x['percent']:5.1f}% "
            f"{self.bytes(x['free'])} free"
            for x in get_filesystems()
        ) or "No filesystems."

    def collect_usb(self):
        return "\n".join(
            f"{x['bus']}:{x['device']}  "
            f"{x['id']}  "
            f"{x['name']}"
            for x in get_usb()
        ) or "No USB devices."

    def collect_pci(self):
        return "\n".join(
            f"{x['slot']:<15} "
            f"{x['class']:<25} "
            f"{x['vendor']} "
            f"{x['device']}"
            for x in get_pci()
        ) or "No PCI devices."

    def collect_battery(self):
        b = get_battery()

        if not b:
            return "No battery detected."

        return (
            f"Charge    "
            f"{b['percent']:.1f}%\n"
            f"{self.bar(b['percent'])}\n"
            f"Status    "
            f"{'Charging / AC' if b['plugged'] else 'Discharging'}\n"
            f"Time      "
            f"{self.seconds(b['seconds_left'])}"
        )

    def collect_audio(self):
        return (
            "\n".join(get_audio())
            or "No audio information."
        )

    def collect_bluetooth(self):
        return "\n".join(
            f"{x['mac']:<18} "
            f"{x['name']}"
            for x in get_bluetooth()
        ) or "No Bluetooth devices."

    def collect_wifi(self):
        lines = []

        for x in get_wifi():
            lines.append(
                f"{x['name']:<12} "
                f"{'CONNECTED' if x['connected'] else 'DISCONNECTED'}"
            )

            if x.get("link"):
                lines.append(
                    f"  {x['link']}"
                )

        return (
            "\n".join(lines)
            or "No Wi-Fi interfaces."
        )

    def collect_users(self):
        return "\n".join(
            f"{x['name']:<20} "
            f"{str(x['terminal']):<10} "
            f"{str(x['host']):<20} "
            f"PID {x['pid']}"
            for x in get_users()
        ) or "No logged-in users."

    def collect_logs(self):
        return (
            "\n".join(get_logs(20))
            or "No logs."
        )

    def collect_kernel(self):
        k = get_kernel()

        return (
            f"Release       {k['release']}\n"
            f"Version       {k['version']}\n"
            f"Machine       {k['machine']}\n"
            f"Command line  {k['cmdline']}\n\n"
            f"Loaded modules: "
            f"{len(k['modules'])}"
        )

    def collect_process_tree(self):
        tree = get_process_tree()
        lines = []

        for pid, children in tree.items():
            if children:
                names = ", ".join(
                    f"{x['name']}({x['pid']})"
                    for x in children[:8]
                )

                lines.append(
                    f"{pid:<8} → {names}"
                )

        return (
            "\n".join(lines[:80])
            or "No process tree."
        )

    def collect_containers(self):
        return "\n".join(
            f"{x['id'][:12]:12} "
            f"{x['name']:<20} "
            f"{x['status']:<25} "
            f"{x['image']}"
            for x in get_containers()
        ) or "No containers."

    def collect_virtualization(self):
        x = get_virtualization()

        return (
            f"Virtualization  "
            f"{x['virtualization']}\n"
            f"KVM             "
            f"{'available' if x['kvm'] else 'unavailable'}\n"
            f"Hypervisor      "
            f"{'present' if x['hypervisor'] else 'not detected'}"
        )

    def collect_packages(self):
        x = get_packages()

        return (
            f"Manager   "
            f"{x['manager'] or 'none'}\n"
            f"Packages  "
            f"{len(x['packages']):,}\n\n"
            + "\n".join(
                x["packages"][:50]
            )
        )

    def collect_mounts(self):
        return "\n".join(
            f"{x['device']:<25} "
            f"{x['mount']:<30} "
            f"{x['fstype']:<10} "
            f"{x['options']}"
            for x in get_mounts()
        ) or "No mounts."

    def collect_cron(self):
        t, c = (
            get_timers(),
            get_crontab(),
        )

        if not t and not c:
            return "No timers or crontab."

        return (
            "SYSTEMD TIMERS\n"
            + "\n".join(t[:30])
            + "\n\nCRONTAB\n"
            + "\n".join(c)
        )

    def collect_gpu_processes(self):
        return "\n".join(
            f"{x['pid']:<8} "
            f"{x['name']:<35} "
            f"{x['vram']:>8} MiB"
            for x in get_gpu_processes()
        ) or "No GPU processes."

    def collect_ai(self):
        return "\n".join(
            f"{x['pid']:<8} "
            f"{x['name']:<20} "
            f"CPU {x['cpu']:5.1f}% "
            f"RAM {self.bytes(x['memory'])}"
            for x in get_ai_processes()
        ) or "No AI processes detected."

    def collect_ollama(self):
        return "\n".join(
            f"{x.get('name', '?'):<35} "
            f"{x.get('size', '?')} "
            f"{x.get('expires_at', '')}"
            for x in get_ollama()
        ) or "Ollama is not running."

    def collect_cuda(self):
        x = get_cuda()

        if not x:
            return "NVIDIA CUDA unavailable."

        return "\n".join(
            f"{g['name']}\n"
            f"Driver    {g['driver']}\n"
            f"CUDA      {g['cuda']}"
            for g in x
        )

    def collect_pytorch(self):
        x = get_pytorch()

        lines = [
            f"PyTorch   "
            f"{x['version'] or 'not installed'}",
            f"CUDA      "
            f"{x['cuda'] or 'none'}",
            f"Available "
            f"{'YES' if x['available'] else 'NO'}",
        ]

        for g in x["gpus"]:
            lines += [
                "",
                f"GPU {g['index']}  "
                f"{g['name']}",
                f"VRAM      "
                f"{self.bytes(g['memory'])}",
            ]

        return "\n".join(lines)

    @staticmethod
    def bar(value, width=18):
        value = max(
            0,
            min(100, float(value)),
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


if __name__ == "__main__":
    Nuxora().run()

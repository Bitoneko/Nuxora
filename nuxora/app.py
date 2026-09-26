import json
import os
import time

from textual import work
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
        overflow-y: auto;
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
                        value=self.main_app.collector_visibility.get(key, True),
                        id=f"check-{key}"
                    )

            with Horizontal(id="buttons"):
                yield Button("Apply", variant="primary", id="apply")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event):
        if event.button.id == "cancel":
            self.dismiss()
            return

        for key, _ in self.main_app.collectors:
            box = self.query_one(f"#check-{key}", Checkbox)
            self.main_app.collector_visibility[key] = box.value
            self.main_app.set_panel_visible(key, box.value)

        self.main_app.save_visibility()
        self.dismiss()


class Nuxora(App):
    TITLE = "Nuxora"
    SUB_TITLE = "Real-time Linux System Monitor"

    CSS = """
    Screen {
        background: $background;
    }

    #dashboard {
        height: 1fr;
        padding: 0 1;
        overflow-y: auto;
    }

    .row {
        width: 1fr;
        height: 15;
    }

    .panel {
        width: 1fr;
        height: 14;
        border: solid $accent;
        padding: 0 1;
        margin: 0 1 1 0;
        overflow: hidden;
    }

    .title {
        height: 2;
        text-style: bold;
        color: $accent;
        overflow: hidden;
    }

    .body {
        height: 1fr;
        overflow: hidden;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
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

    intervals = {
        "system": 2,
        "cpu": 1,
        "memory": 2,
        "gpu": 2,
        "network": 2,
        "disk": 5,
        "processes": 3,
        "sensors": 5,
        "battery": 5,
        "wifi": 5,
        "gpu_processes": 3,
        "ai": 5,
        "pytorch": 15,
        "services": 15,
        "filesystem": 20,
        "usb": 20,
        "pci": 30,
        "audio": 20,
        "bluetooth": 20,
        "users": 15,
        "logs": 15,
        "kernel": 30,
        "process_tree": 10,
        "containers": 10,
        "virtualization": 30,
        "packages": 60,
        "mounts": 20,
        "cron": 30,
        "ollama": 10,
        "cuda": 15,
    }

    def __init__(self):
        super().__init__()

        self.config_path = os.path.expanduser(
            "~/.config/nuxora/visibility.json"
        )

        self.collector_visibility = self.load_visibility()
        self.last_update = {}
        self.running = set()

        self._net = None
        self._net_t = time.monotonic()

    def compose(self) -> ComposeResult:
        yield Header()

        with ScrollableContainer(id="dashboard"):
            for start in range(0, len(self.collectors), 3):
                with Horizontal(classes="row"):
                    for key, name in self.collectors[start:start + 3]:
                        yield Vertical(
                            Static(name.upper(), classes="title"),
                            Static("", id=f"panel-{key}", classes="body"),
                            classes="panel",
                        )

        yield Footer()

    def on_mount(self):
        for key, _ in self.collectors:
            self.set_panel_visible(
                key,
                self.collector_visibility.get(key, True),
            )

        self.update_all()
        self.set_interval(1, self.tick)

    def action_refresh(self):
        self.update_all(force=True)

    def action_settings(self):
        self.push_screen(SettingsScreen(self))

    def tick(self):
        now = time.monotonic()

        for key, _ in self.collectors:
            if not self.enabled(key):
                continue

            interval = self.intervals.get(key, 10)
            previous = self.last_update.get(key, 0)

            if now - previous >= interval:
                self.last_update[key] = now
                self.start_collector(key)

    def update_all(self, force=False):
        now = time.monotonic()

        for key, _ in self.collectors:
            if not self.enabled(key):
                continue

            if force:
                self.last_update[key] = now
                self.start_collector(key)
                continue

            interval = self.intervals.get(key, 10)

            if now - self.last_update.get(key, 0) >= interval:
                self.last_update[key] = now
                self.start_collector(key)

    def start_collector(self, key):
        if key in self.running:
            return

        self.running.add(key)
        self.run_collector(key)

    @work(thread=True, exclusive=False)
    def run_collector(self, key):
        try:
            method = getattr(self, f"collect_{key}")
            value = method()

            self.call_from_thread(
                self.set,
                key,
                value,
            )
        except Exception as e:
            self.call_from_thread(
                self.set,
                key,
                f"Collector error:\n{type(e).__name__}: {e}",
            )
        finally:
            self.running.discard(key)

    def load_visibility(self):
        result = {key: True for key, _ in self.collectors}

        try:
            with open(self.config_path) as f:
                data = json.load(f)

            if isinstance(data, dict):
                for key in result:
                    if key in data:
                        result[key] = bool(data[key])

        except Exception:
            pass

        return result

    def save_visibility(self):
        os.makedirs(
            os.path.dirname(self.config_path),
            exist_ok=True,
        )

        with open(self.config_path, "w") as f:
            json.dump(
                self.collector_visibility,
                f,
                indent=2,
            )

    def enabled(self, key):
        return self.collector_visibility.get(key, True)

    def set_panel_visible(self, key, value):
        try:
            panel = self.query_one(f"#panel-{key}")
            panel.parent.display = bool(value)
        except Exception:
            pass

    def set(self, key, value):
        try:
            self.query_one(f"#panel-{key}").update(value)
        except Exception:
            pass

    def collect_system(self):
        s = get_system()

        battery = ""

        if s.get("battery") is not None:
            battery = (
                f"\nBattery   {s['battery']:.0f}%"
                + (" Charging" if s.get("charging") else "")
            )

        return (
            f"OS        {s.get('os', '?')}\n"
            f"Kernel    {s.get('kernel', '?')}\n"
            f"Machine   {s.get('machine', '?')}\n"
            f"Host      {s.get('host', '?')}\n"
            f"Uptime    {s.get('uptime', '?')}\n"
            f"Time      {s.get('time', '?')}\n"
            f"Users     {s.get('users', '?')}\n"
            f"Boot      {s.get('boot', '?')}"
            f"{battery}"
        )

    def collect_cpu(self):
        c = get_cpu()

        cores = c.get("cores", [])
        count = c.get("count", len(cores))
        physical = c.get("physical", count)
        frequency = c.get("frequency")
        load = c.get("load", (0, 0, 0))

        lines = [
            f"Total     {c.get('total', 0):5.1f}%",
            f"Cores     {count} ({physical} physical)",
        ]

        if frequency:
            lines += [
                f"Clock     {frequency.current:5.0f} MHz",
                f"Max       {frequency.max:5.0f} MHz",
            ]

        lines += [
            "",
            *[
                f"{i:02d} {self.bar(v, 20)} {v:5.1f}%"
                for i, v in enumerate(cores)
            ],
            "",
            f"Load      {load[0]:.2f} {load[1]:.2f} {load[2]:.2f}",
        ]

        return "\n".join(lines)

    def collect_memory(self):
        m = get_memory()

        if isinstance(m, tuple):
            ram, swap = m
        else:
            ram = m.get("ram")
            swap = m.get("swap")

        if ram is None or swap is None:
            return "Memory information unavailable."

        return (
            f"RAM       {self.bytes(ram.used)} / {self.bytes(ram.total)}\n"
            f"Usage     {ram.percent:5.1f}%\n"
            f"{self.bar(ram.percent)}\n\n"
            f"Available {self.bytes(ram.available)}\n"
            f"Cached    {self.bytes(getattr(ram, 'cached', 0))}\n"
            f"Buffers   {self.bytes(getattr(ram, 'buffers', 0))}\n"
            f"Shared    {self.bytes(getattr(ram, 'shared', 0))}\n\n"
            f"SWAP      {self.bytes(swap.used)} / {self.bytes(swap.total)}\n"
            f"Usage     {swap.percent:5.1f}%\n"
            f"{self.bar(swap.percent)}"
        )

    def collect_gpu(self):
        gpus = get_gpu()

        if not gpus:
            return "NVIDIA GPU unavailable."

        lines = []

        for i, gpu in enumerate(gpus):
            used = gpu.get("vram_used", 0)
            total = gpu.get("vram_total", 0)

            usage = used / total * 100 if total else 0

            lines += [
                gpu.get("name", "?"),
                f"GPU       {gpu.get('gpu', 0):5.1f}%",
                f"VRAM      {self.bytes(used)} / {self.bytes(total)}",
                f"Usage     {usage:5.1f}%",
                self.bar(usage),
                f"Temp      {gpu.get('temp', 0)}°C",
                f"Power     {gpu.get('power', 0):.1f} W",
                f"Clock     {gpu.get('clock', 0)} MHz",
                f"Mem Clock {gpu.get('memclock', 0)} MHz",
            ]

            if gpu.get("fan") is not None:
                lines.append(f"Fan       {gpu['fan']}%")

            if i < len(gpus) - 1:
                lines.append("")

        return "\n".join(lines)

    def collect_disk(self):
        lines = []

        for d in get_disks():
            lines += [
                d.get("device", "?"),
                d.get("mount", "?"),
                f"{self.bar(d.get('percent', 0))} "
                f"{d.get('percent', 0):5.1f}%",
                f"Used      {self.bytes(d.get('used', 0))}",
                f"Free      {self.bytes(d.get('free', 0))}",
                f"Total     {self.bytes(d.get('total', 0))}",
                f"Type      {d.get('fstype', '?')}",
                "",
            ]

        io = get_io()

        if io:
            lines += [
                f"Read      {self.bytes(io.read_bytes)}",
                f"Write     {self.bytes(io.write_bytes)}",
            ]

        devices = get_devices()

        if devices:
            lines.append("")
            lines.append("BLOCK DEVICES")

            for d in devices:
                lines.append(
                    f"{d.get('path', d.get('name', '?')):16} "
                    f"{d.get('size', '?'):>9} "
                    f"{d.get('type', '?'):6} "
                    f"{d.get('model') or ''}"
                )

        return "\n".join(lines) or "No disks."

    def collect_network(self):
        n = get_network()
        total = n["total"]
        now = time.monotonic()

        if self._net is None:
            self._net = total
            self._net_t = now

        dt = max(now - self._net_t, 0.001)

        rx = (total.bytes_recv - self._net.bytes_recv) / dt
        tx = (total.bytes_sent - self._net.bytes_sent) / dt

        self._net = total
        self._net_t = now

        lines = [
            f"Download   {self.bytes(rx)}/s",
            f"Upload     {self.bytes(tx)}/s",
            "",
            f"Total RX   {self.bytes(total.bytes_recv)}",
            f"Total TX   {self.bytes(total.bytes_sent)}",
            "",
            f"Packets RX {total.packets_recv:,}",
            f"Packets TX {total.packets_sent:,}",
            f"Errors RX  {total.errin:,}",
            f"Errors TX  {total.errout:,}",
            "",
        ]

        for name, interface in n["interfaces"].items():
            lines.append(
                f"{name[:12]:12} "
                f"↓{self.bytes(interface.bytes_recv)} "
                f"↑{self.bytes(interface.bytes_sent)}"
            )

        lines += [
            "",
            f"Connections {len(n['connections'])}",
        ]

        return "\n".join(lines)

    def collect_processes(self):
        processes = get_processes()[:25]

        lines = [
            "PID       PROCESS                       CPU      RAM       MEMORY       STATUS"
        ]

        for p in processes:
            lines.append(
                f"{p['pid']:<9}"
                f"{p['name'][:28]:<29}"
                f"{p['cpu']:>5.1f}%   "
                f"{p['ram']:>5.1f}%   "
                f"{self.bytes(p['memory']):>10}   "
                f"{p['status']}"
            )

        return "\n".join(lines)

    def collect_sensors(self):
        s = get_sensors()
        lines = []

        for chip, items in s["temperatures"].items():
            lines.append(chip)

            for x in items:
                high = (
                    f"  high {x['high']:.1f}°C"
                    if x["high"]
                    else ""
                )

                lines.append(
                    f"  {x['label'] or '?':20} "
                    f"{x['current']:6.1f}°C{high}"
                )

        for items in s["fans"].values():
            for x in items:
                lines.append(
                    f"  FAN {x['label'] or '?':16} "
                    f"{x['current']:6.0f} RPM"
                )

        return "\n".join(lines) or "No sensors found."

    def collect_services(self):
        return "\n".join(
            f"{s['name']:<40} "
            f"{s['active']:<8} "
            f"{s['sub']:<10} "
            f"{s['description']}"
            for s in get_services()[:100]
        ) or "No services found."

    def collect_filesystem(self):
        return "\n".join(
            f"{f['mount']:<25} "
            f"{f['fstype']:<8} "
            f"{self.bar(f['percent'], 16)} "
            f"{f['percent']:5.1f}% "
            f"{self.bytes(f['free'])} free"
            for f in get_filesystems()
        ) or "No filesystems."

    def collect_usb(self):
        return "\n".join(
            f"{d['bus']}:{d['device']} "
            f"{d['id']} "
            f"{d['name']}"
            for d in get_usb()
        ) or "No USB devices."

    def collect_pci(self):
        return "\n".join(
            f"{d['slot']:<15} "
            f"{d['class']:<25} "
            f"{d['vendor']} "
            f"{d['device']}"
            for d in get_pci()
        ) or "No PCI devices."

    def collect_battery(self):
        b = get_battery()

        if not b:
            return "No battery detected."

        return (
            f"Charge    {b['percent']:.1f}%\n"
            f"{self.bar(b['percent'])}\n"
            f"Status    "
            f"{'Charging / AC' if b['plugged'] else 'Discharging'}\n"
            f"Time      {self.seconds(b['seconds_left'])}"
        )

    def collect_audio(self):
        return "\n".join(get_audio()) or "No audio information."

    def collect_bluetooth(self):
        return "\n".join(
            f"{d['mac']:<18} {d['name']}"
            for d in get_bluetooth()
        ) or "No Bluetooth devices."

    def collect_wifi(self):
        lines = []

        for i in get_wifi():
            lines.append(
                f"{i['name']:<12} "
                f"{'CONNECTED' if i['connected'] else 'DISCONNECTED'}"
            )

            if i.get("link"):
                lines.append(f"  {i['link']}")

        return "\n".join(lines) or "No Wi-Fi interfaces."

    def collect_users(self):
        return "\n".join(
            f"{u['name']:<20} "
            f"{str(u['terminal']):<10} "
            f"{str(u['host']):<20} "
            f"PID {u['pid']}"
            for u in get_users()
        ) or "No logged-in users."

    def collect_logs(self):
        return "\n".join(get_logs(20)) or "No logs."

    def collect_kernel(self):
        k = get_kernel()

        return (
            f"Release       {k['release']}\n"
            f"Version       {k['version']}\n"
            f"Machine       {k['machine']}\n"
            f"Command line  {k['cmdline']}\n\n"
            f"Loaded modules: {len(k['modules'])}"
        )

    def collect_process_tree(self):
        tree = get_process_tree()
        lines = []

        for pid, children in tree.items():
            if not children:
                continue

            names = ", ".join(
                f"{x['name']}({x['pid']})"
                for x in children[:8]
            )

            lines.append(
                f"{pid:<8} → {names}"
            )

        return "\n".join(lines[:80]) or "No process tree."

    def collect_containers(self):
        return "\n".join(
            f"{c['id'][:12]:12} "
            f"{c['name']:<20} "
            f"{c['status']:<25} "
            f"{c['image']}"
            for c in get_containers()
        ) or "No containers."

    def collect_virtualization(self):
        v = get_virtualization()

        return (
            f"Virtualization  {v['virtualization']}\n"
            f"KVM             "
            f"{'available' if v['kvm'] else 'unavailable'}\n"
            f"Hypervisor      "
            f"{'present' if v['hypervisor'] else 'not detected'}"
        )

    def collect_packages(self):
        p = get_packages()

        return (
            f"Manager   {p['manager'] or 'none'}\n"
            f"Packages  {len(p['packages']):,}\n\n"
            + "\n".join(p["packages"][:50])
        )

    def collect_mounts(self):
        return "\n".join(
            f"{m['device']:<25} "
            f"{m['mount']:<30} "
            f"{m['fstype']:<10} "
            f"{m['options']}"
            for m in get_mounts()
        ) or "No mounts."

    def collect_cron(self):
        timers = get_timers()
        cron = get_crontab()

        if not timers and not cron:
            return "No timers or crontab."

        return (
            "SYSTEMD TIMERS\n"
            + "\n".join(timers[:30])
            + "\n\nCRONTAB\n"
            + "\n".join(cron)
        )

    def collect_gpu_processes(self):
        return "\n".join(
            f"{p['pid']:<8} "
            f"{p['name']:<35} "
            f"{p['vram']:>8} MiB"
            for p in get_gpu_processes()
        ) or "No GPU processes."

    def collect_ai(self):
        return "\n".join(
            f"{p['pid']:<8} "
            f"{p['name']:<20} "
            f"CPU {p['cpu']:5.1f}% "
            f"RAM {self.bytes(p['memory'])}"
            for p in get_ai_processes()
        ) or "No AI processes detected."

    def collect_ollama(self):
        return "\n".join(
            f"{m.get('name', '?'):<35} "
            f"{m.get('size', '?')} "
            f"{m.get('expires_at', '')}"
            for m in get_ollama()
        ) or "Ollama is not running."

    def collect_cuda(self):
        cuda = get_cuda()

        if not cuda:
            return "NVIDIA CUDA unavailable."

        lines = []

        for g in cuda:
            lines += [
                g.get("name", "?"),
                f"Driver    {g.get('driver', '?')}",
                f"CUDA      {g.get('cuda', '?')}",
            ]

        return "\n".join(lines)

    def collect_pytorch(self):
        p = get_pytorch()

        lines = [
            f"PyTorch   {p.get('version') or 'not installed'}",
            f"CUDA      {p.get('cuda') or 'none'}",
            f"Available {'YES' if p.get('available') else 'NO'}",
        ]

        for g in p.get("gpus", []):
            lines += [
                "",
                f"GPU {g.get('index', '?')}  {g.get('name', '?')}",
                f"VRAM      {self.bytes(g.get('memory', 0))}",
            ]

        return "\n".join(lines)

    @staticmethod
    def bar(value, width=18):
        value = max(0, min(100, float(value)))
        filled = int(width * value / 100)
        return "█" * filled + "░" * (width - filled)

    @staticmethod
    def bytes(value):
        value = float(value)

        for unit in ("B", "KB", "MB", "GB", "TB"):
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

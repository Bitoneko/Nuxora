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
        background: rgba(0,0,0,.7);
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
    }
    .panel {
        width: 1fr;
        min-height: 12;
        border: solid $accent;
        padding: 0 1;
        margin: 0 1 1 0;
    }
    .title {
        height: 2;
        text-style: bold;
        color: $accent;
    }
    Static {
        height: auto;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("ctrl+p", "settings", "Settings")
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
        ("pytorch", "PyTorch")
    ]

    def __init__(self):
        super().__init__()
        self.config_path = os.path.expanduser(
            "~/.config/nuxora/visibility.json"
        )
        self.collector_visibility = self.load_visibility()

    def compose(self) -> ComposeResult:
        yield Header()

        with ScrollableContainer(id="dashboard"):
            for key, name in self.collectors:
                yield Vertical(
                    Static(name.upper(), classes="title"),
                    Static(id=f"panel-{key}"),
                    classes="panel"
                )

        yield Footer()

    def on_mount(self):
        for key, _ in self.collectors:
            self.set_panel_visible(
                key,
                self.collector_visibility.get(key, True)
            )

        self.update_all()
        self.set_interval(1, self.update_all)

    def action_refresh(self):
        self.update_all()

    def action_settings(self):
        self.push_screen(SettingsScreen(self))

    def load_visibility(self):
        default = {key: True for key, _ in self.collectors}

        try:
            with open(self.config_path) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    default.update(data)
        except Exception:
            pass

        return default

    def save_visibility(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump(self.collector_visibility, f, indent=2)

    def set_panel_visible(self, key, value):
        try:
            self.query_one(f"#panel-{key}").parent.display = value
        except Exception:
            try:
                self.query_one(f"#panel-{key}").display = value
            except Exception:
                pass

    def set(self, key, text):
        try:
            self.query_one(f"#panel-{key}").update(text)
        except Exception:
            pass

    def update_all(self):
        self.update_system()
        self.update_cpu()
        self.update_memory()
        self.update_gpu()
        self.update_disk()
        self.update_network()
        self.update_processes()
        self.update_sensors()
        self.update_services()
        self.update_filesystem()
        self.update_usb()
        self.update_pci()
        self.update_battery()
        self.update_audio()
        self.update_bluetooth()
        self.update_wifi()
        self.update_users()
        self.update_logs()
        self.update_kernel()
        self.update_process_tree()
        self.update_containers()
        self.update_virtualization()
        self.update_packages()
        self.update_mounts()
        self.update_cron()
        self.update_gpu_processes()
        self.update_ai()
        self.update_ollama()
        self.update_cuda()
        self.update_pytorch()

    def update_system(self):
        s = get_system()
        battery = ""

        if s.get("battery") is not None:
            battery = (
                f"\nBattery   {s['battery']:.0f}%"
                + (" Charging" if s.get("charging") else "")
            )

        self.set(
            "system",
            f"OS        {s['os']}\n"
            f"Kernel    {s['kernel']}\n"
            f"Machine   {s['machine']}\n"
            f"Host      {s['host']}\n"
            f"Uptime    {s['uptime']}\n"
            f"Time      {s['time']}\n"
            f"Users     {s['users']}\n"
            f"Boot      {s['boot']}{battery}"
        )

    def update_cpu(self):
        c = get_cpu()
        frequency = c["frequency"]

        lines = [
            f"Total     {c['total']:5.1f}%",
            f"Cores     {c['count']} ({c['physical']} physical)"
        ]

        if frequency:
            lines += [
                f"Clock     {frequency.current:5.0f} MHz",
                f"Max       {frequency.max:5.0f} MHz"
            ]

        lines += [
            "",
            *[
                f"{i:02d} {self.bar(value, 20)} {value:5.1f}%"
                for i, value in enumerate(c["cores"])
            ],
            "",
            f"Load      {c['load'][0]:.2f} "
            f"{c['load'][1]:.2f} {c['load'][2]:.2f}"
        ]

        self.set("cpu", "\n".join(lines))

    def update_memory(self):
        m = get_memory()
        ram = m["ram"]
        swap = m["swap"]

        self.set(
            "memory",
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

    def update_gpu(self):
        gpus = get_gpu()

        if not gpus:
            self.set("gpu", "NVIDIA GPU unavailable.")
            return

        lines = []

        for i, gpu in enumerate(gpus):
            usage = (
                gpu["vram_used"] / gpu["vram_total"] * 100
                if gpu["vram_total"] else 0
            )

            lines += [
                gpu["name"],
                f"GPU       {gpu['gpu']:5.1f}%",
                f"VRAM      {self.bytes(gpu['vram_used'])} / "
                f"{self.bytes(gpu['vram_total'])}",
                f"Usage     {usage:5.1f}%\n{self.bar(usage)}",
                f"Temp      {gpu['temp']}°C",
                f"Power     {gpu['power']:.1f} W",
                f"Clock     {gpu['clock']} MHz",
                f"Mem Clock {gpu['memclock']} MHz"
            ]

            if gpu["fan"] is not None:
                lines.append(f"Fan       {gpu['fan']}%")

            if i < len(gpus) - 1:
                lines.append("")

        self.set("gpu", "\n".join(lines))

    def update_disk(self):
        lines = []

        for disk in get_disks():
            lines += [
                disk["device"],
                disk["mount"],
                f"{self.bar(disk['percent'])} {disk['percent']:5.1f}%",
                f"Used      {self.bytes(disk['used'])}",
                f"Free      {self.bytes(disk['free'])}",
                f"Total     {self.bytes(disk['total'])}",
                f"Type      {disk['fstype']}",
                ""
            ]

        io = get_io()

        if io:
            lines += [
                f"Read      {self.bytes(io.read_bytes)}",
                f"Write     {self.bytes(io.write_bytes)}"
            ]

        devices = get_devices()

        if devices:
            lines += ["", "BLOCK DEVICES"]

            for device in devices:
                lines.append(
                    f"{device.get('path', device.get('name', '?')):16} "
                    f"{device.get('size', '?'):>9} "
                    f"{device.get('type', '?'):6} "
                    f"{device.get('model') or ''}"
                )

        self.set("disk", "\n".join(lines))

    def update_network(self):
        network = get_network()
        total = network["total"]
        now = time.monotonic()

        if not hasattr(self, "_net"):
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
            ""
        ]

        for name, interface in network["interfaces"].items():
            lines.append(
                f"{name[:12]:12} "
                f"↓{self.bytes(interface.bytes_recv)} "
                f"↑{self.bytes(interface.bytes_sent)}"
            )

        lines += ["", f"Connections {len(network['connections'])}"]
        self.set("network", "\n".join(lines))

    def update_processes(self):
        processes = get_processes()[:25]

        lines = [
            "PID       PROCESS                       CPU      RAM       "
            "MEMORY       STATUS"
        ]

        lines += [
            f"{process['pid']:<9}"
            f"{process['name'][:28]:<29}"
            f"{process['cpu']:>5.1f}%   "
            f"{process['ram']:>5.1f}%   "
            f"{self.bytes(process['memory']):>10}   "
            f"{process['status']}"
            for process in processes
        ]

        self.set("processes", "\n".join(lines))

    def update_sensors(self):
        sensors = get_sensors()
        lines = []

        for chip, items in sensors["temperatures"].items():
            lines.append(chip)

            for sensor in items:
                high = (
                    f"  high {sensor['high']:.1f}°C"
                    if sensor["high"] else ""
                )
                lines.append(
                    f"  {sensor['label'] or '?':20} "
                    f"{sensor['current']:6.1f}°C{high}"
                )

        for _, items in sensors["fans"].items():
            for fan in items:
                lines.append(
                    f"  FAN {fan['label'] or '?':16} "
                    f"{fan['current']:6.0f} RPM"
                )

        self.set("sensors", "\n".join(lines) or "No sensors found.")

    def update_services(self):
        services = get_services()
        lines = [
            f"{service['name']:<40} "
            f"{service['active']:<8} "
            f"{service['sub']:<10} "
            f"{service['description']}"
            for service in services
        ]

        self.set("services", "\n".join(lines) or "No services found.")

    def update_filesystem(self):
        lines = [
            f"{fs['mount']:<25} "
            f"{fs['fstype']:<8} "
            f"{self.bar(fs['percent'], 16)} "
            f"{fs['percent']:5.1f}%  "
            f"{self.bytes(fs['free'])} free"
            for fs in get_filesystems()
        ]

        self.set("filesystem", "\n".join(lines) or "No filesystems.")

    def update_usb(self):
        lines = [
            f"{device['bus']}:{device['device']}  "
            f"{device['id']}  {device['name']}"
            for device in get_usb()
        ]

        self.set("usb", "\n".join(lines) or "No USB devices.")

    def update_pci(self):
        lines = [
            f"{device['slot']:<15} "
            f"{device['class']:<25} "
            f"{device['vendor']} {device['device']}"
            for device in get_pci()
        ]

        self.set("pci", "\n".join(lines) or "No PCI devices.")

    def update_battery(self):
        battery = get_battery()

        if not battery:
            self.set("battery", "No battery detected.")
            return

        self.set(
            "battery",
            f"Charge    {battery['percent']:.1f}%\n"
            f"{self.bar(battery['percent'])}\n"
            f"Status    "
            f"{'Charging / AC' if battery['plugged'] else 'Discharging'}\n"
            f"Time      {self.seconds(battery['seconds_left'])}"
        )

    def update_audio(self):
        self.set(
            "audio",
            "\n".join(get_audio()) or "No audio information."
        )

    def update_bluetooth(self):
        lines = [
            f"{device['mac']:<18} {device['name']}"
            for device in get_bluetooth()
        ]

        self.set(
            "bluetooth",
            "\n".join(lines) or "No Bluetooth devices."
        )

    def update_wifi(self):
        lines = []

        for interface in get_wifi():
            lines.append(
                f"{interface['name']:<12} "
                f"{'CONNECTED' if interface['connected'] else 'DISCONNECTED'}"
            )

            if interface.get("link"):
                lines.append(f"  {interface['link']}")

        self.set("wifi", "\n".join(lines) or "No Wi-Fi interfaces.")

    def update_users(self):
        lines = [
            f"{user['name']:<20} "
            f"{str(user['terminal']):<10} "
            f"{str(user['host']):<20} "
            f"PID {user['pid']}"
            for user in get_users()
        ]

        self.set("users", "\n".join(lines) or "No logged-in users.")

    def update_logs(self):
        self.set("logs", "\n".join(get_logs(20)) or "No logs.")

    def update_kernel(self):
        kernel = get_kernel()

        self.set(
            "kernel",
            f"Release       {kernel['release']}\n"
            f"Version       {kernel['version']}\n"
            f"Machine       {kernel['machine']}\n"
            f"Command line  {kernel['cmdline']}\n\n"
            f"Loaded modules: {len(kernel['modules'])}"
        )

    def update_process_tree(self):
        tree = get_process_tree()
        lines = []

        for pid, children in tree.items():
            if not children:
                continue

            names = ", ".join(
                f"{child['name']}({child['pid']})"
                for child in children[:8]
            )
            lines.append(f"{pid:<8} → {names}")

        self.set(
            "process_tree",
            "\n".join(lines[:80]) or "No process tree."
        )

    def update_containers(self):
        lines = [
            f"{container['id'][:12]:12} "
            f"{container['name']:<20} "
            f"{container['status']:<25} "
            f"{container['image']}"
            for container in get_containers()
        ]

        self.set(
            "containers",
            "\n".join(lines) or "No containers."
        )

    def update_virtualization(self):
        virtualization = get_virtualization()

        self.set(
            "virtualization",
            f"Virtualization  {virtualization['virtualization']}\n"
            f"KVM             "
            f"{'available' if virtualization['kvm'] else 'unavailable'}\n"
            f"Hypervisor      "
            f"{'present' if virtualization['hypervisor'] else 'not detected'}"
        )

    def update_packages(self):
        packages = get_packages()

        self.set(
            "packages",
            f"Manager   {packages['manager'] or 'none'}\n"
            f"Packages  {len(packages['packages']):,}\n\n"
            + "\n".join(packages["packages"][:50])
        )

    def update_mounts(self):
        lines = [
            f"{mount['device']:<25} "
            f"{mount['mount']:<30} "
            f"{mount['fstype']:<10} "
            f"{mount['options']}"
            for mount in get_mounts()
        ]

        self.set("mounts", "\n".join(lines) or "No mounts.")

    def update_cron(self):
        timers = get_timers()
        crontab = get_crontab()

        if not timers and not crontab:
            self.set("cron", "No timers or crontab.")
            return

        self.set(
            "cron",
            "SYSTEMD TIMERS\n"
            + "\n".join(timers[:30])
            + "\n\nCRONTAB\n"
            + "\n".join(crontab)
        )

    def update_gpu_processes(self):
        lines = [
            f"{process['pid']:<8} "
            f"{process['name']:<35} "
            f"{process['vram']:>8} MiB"
            for process in get_gpu_processes()
        ]

        self.set(
            "gpu_processes",
            "\n".join(lines) or "No GPU processes."
        )

    def update_ai(self):
        lines = [
            f"{process['pid']:<8} "
            f"{process['name']:<20} "
            f"CPU {process['cpu']:5.1f}%  "
            f"RAM {self.bytes(process['memory'])}"
            for process in get_ai_processes()
        ]

        self.set(
            "ai",
            "\n".join(lines) or "No AI processes detected."
        )

    def update_ollama(self):
        lines = [
            f"{model.get('name', '?'):<35} "
            f"{model.get('size', '?')}  "
            f"{model.get('expires_at', '')}"
            for model in get_ollama()
        ]

        self.set(
            "ollama",
            "\n".join(lines) or "Ollama is not running."
        )

    def update_cuda(self):
        cuda = get_cuda()

        if not cuda:
            self.set("cuda", "NVIDIA CUDA unavailable.")
            return

        self.set(
            "cuda",
            "\n".join(
                f"{gpu['name']}\n"
                f"Driver    {gpu['driver']}\n"
                f"CUDA      {gpu['cuda']}"
                for gpu in cuda
            )
        )

    def update_pytorch(self):
        pytorch = get_pytorch()

        lines = [
            f"PyTorch   {pytorch['version'] or 'not installed'}",
            f"CUDA      {pytorch['cuda'] or 'none'}",
            f"Available {'YES' if pytorch['available'] else 'NO'}"
        ]

        for gpu in pytorch["gpus"]:
            lines += [
                "",
                f"GPU {gpu['index']}  {gpu['name']}",
                f"VRAM      {self.bytes(gpu['memory'])}"
            ]

        self.set("pytorch", "\n".join(lines))

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

        return time.strftime("%H:%M:%S", time.gmtime(value))


if __name__ == "__main__":
    Nuxora().run()

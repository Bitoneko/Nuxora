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
        ("ctrl+s", "settings", "Settings")
    ]

    collectors = [
        ("system", "System"), ("cpu", "CPU"), ("memory", "Memory"),
        ("gpu", "GPU"), ("disk", "Disk"), ("network", "Network"),
        ("processes", "Processes"), ("sensors", "Sensors"),
        ("services", "Services"), ("filesystem", "Filesystem"),
        ("usb", "USB"), ("pci", "PCI"), ("battery", "Battery"),
        ("audio", "Audio"), ("bluetooth", "Bluetooth"), ("wifi", "Wi-Fi"),
        ("users", "Users"), ("logs", "Logs"), ("kernel", "Kernel"),
        ("process_tree", "Process Tree"), ("containers", "Containers"),
        ("virtualization", "Virtualization"), ("packages", "Packages"),
        ("mounts", "Mounts"), ("cron", "Cron / Timers"),
        ("gpu_processes", "GPU Processes"), ("ai", "AI Processes"),
        ("ollama", "Ollama"), ("cuda", "CUDA"), ("pytorch", "PyTorch")
    ]

    fast = {"system", "cpu", "memory", "gpu", "network"}
    medium = {
        "disk", "processes", "sensors", "battery", "wifi",
        "gpu_processes", "ai", "pytorch"
    }
    slow = {
        "services", "filesystem", "usb", "pci", "audio", "bluetooth",
        "users", "logs", "kernel", "process_tree", "containers",
        "virtualization", "packages", "mounts", "cron", "ollama", "cuda"
    }

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
                key, self.collector_visibility.get(key, True)
            )

        self._net = None
        self._net_t = time.monotonic()

        self.update_all()
        self.set_interval(1, self.update_fast)
        self.set_interval(3, self.update_medium)
        self.set_interval(10, self.update_slow)

    def action_refresh(self):
        self.update_all()

    def action_settings(self):
        self.push_screen(SettingsScreen(self))

    def load_visibility(self):
        result = {key: True for key, _ in self.collectors}
        try:
            with open(self.config_path) as f:
                data = json.load(f)
            if isinstance(data, dict):
                result.update(data)
        except Exception:
            pass
        return result

    def save_visibility(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.collector_visibility, f, indent=2)

    def set_panel_visible(self, key, value):
        try:
            self.query_one(f"#panel-{key}").parent.display = value
        except Exception:
            pass

    def set(self, key, value):
        try:
            self.query_one(f"#panel-{key}").update(value)
        except Exception:
            pass

    def enabled(self, key):
        return self.collector_visibility.get(key, True)

    def update_all(self):
        self.update_fast()
        self.update_medium()
        self.update_slow()

    def update_fast(self):
        if self.enabled("system"):
            self.update_system()
        if self.enabled("cpu"):
            self.update_cpu()
        if self.enabled("memory"):
            self.update_memory()
        if self.enabled("gpu"):
            self.update_gpu()
        if self.enabled("network"):
            self.update_network()

    def update_medium(self):
        if self.enabled("disk"):
            self.update_disk()
        if self.enabled("processes"):
            self.update_processes()
        if self.enabled("sensors"):
            self.update_sensors()
        if self.enabled("battery"):
            self.update_battery()
        if self.enabled("wifi"):
            self.update_wifi()
        if self.enabled("gpu_processes"):
            self.update_gpu_processes()
        if self.enabled("ai"):
            self.update_ai()
        if self.enabled("pytorch"):
            self.update_pytorch()

    def update_slow(self):
        if self.enabled("services"):
            self.update_services()
        if self.enabled("filesystem"):
            self.update_filesystem()
        if self.enabled("usb"):
            self.update_usb()
        if self.enabled("pci"):
            self.update_pci()
        if self.enabled("audio"):
            self.update_audio()
        if self.enabled("bluetooth"):
            self.update_bluetooth()
        if self.enabled("users"):
            self.update_users()
        if self.enabled("logs"):
            self.update_logs()
        if self.enabled("kernel"):
            self.update_kernel()
        if self.enabled("process_tree"):
            self.update_process_tree()
        if self.enabled("containers"):
            self.update_containers()
        if self.enabled("virtualization"):
            self.update_virtualization()
        if self.enabled("packages"):
            self.update_packages()
        if self.enabled("mounts"):
            self.update_mounts()
        if self.enabled("cron"):
            self.update_cron()
        if self.enabled("ollama"):
            self.update_ollama()
        if self.enabled("cuda"):
            self.update_cuda()

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
            f"OS        {s['os']}\nKernel    {s['kernel']}\n"
            f"Machine   {s['machine']}\nHost      {s['host']}\n"
            f"Uptime    {s['uptime']}\nTime      {s['time']}\n"
            f"Users     {s['users']}\nBoot      {s['boot']}{battery}"
        )

    def update_cpu(self):
        c = get_cpu()
        f = c["frequency"]
        lines = [
            f"Total     {c['total']:5.1f}%",
            f"Cores     {c['count']} ({c['physical']} physical)"
        ]
        if f:
            lines += [
                f"Clock     {f.current:5.0f} MHz",
                f"Max       {f.max:5.0f} MHz"
            ]
        lines += [
            "",
            *[
                f"{i:02d} {self.bar(v, 20)} {v:5.1f}%"
                for i, v in enumerate(c["cores"])
            ],
            "",
            f"Load      {c['load'][0]:.2f} {c['load'][1]:.2f} {c['load'][2]:.2f}"
        ]
        self.set("cpu", "\n".join(lines))

    def update_memory(self):
        m = get_memory()
        ram, swap = m["ram"], m["swap"]
        self.set(
            "memory",
            f"RAM       {self.bytes(ram.used)} / {self.bytes(ram.total)}\n"
            f"Usage     {ram.percent:5.1f}%\n{self.bar(ram.percent)}\n\n"
            f"Available {self.bytes(ram.available)}\n"
            f"Cached    {self.bytes(getattr(ram, 'cached', 0))}\n"
            f"Buffers   {self.bytes(getattr(ram, 'buffers', 0))}\n"
            f"Shared    {self.bytes(getattr(ram, 'shared', 0))}\n\n"
            f"SWAP      {self.bytes(swap.used)} / {self.bytes(swap.total)}\n"
            f"Usage     {swap.percent:5.1f}%\n{self.bar(swap.percent)}"
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
                f"VRAM      {self.bytes(gpu['vram_used'])} / {self.bytes(gpu['vram_total'])}",
                f"Usage     {usage:5.1f}%\n{self.bar(usage)}",
                f"Temp      {gpu.get('temp', 0)}°C",
                f"Power     {gpu.get('power', 0):.1f} W",
                f"Clock     {gpu.get('clock', 0)} MHz",
                f"Mem Clock {gpu.get('memclock', 0)} MHz"
            ]
            if gpu.get("fan") is not None:
                lines.append(f"Fan       {gpu['fan']}%")
            if i < len(gpus) - 1:
                lines.append("")
        self.set("gpu", "\n".join(lines))

    def update_disk(self):
        lines = []
        for d in get_disks():
            lines += [
                d["device"], d["mount"],
                f"{self.bar(d['percent'])} {d['percent']:5.1f}%",
                f"Used      {self.bytes(d['used'])}",
                f"Free      {self.bytes(d['free'])}",
                f"Total     {self.bytes(d['total'])}",
                f"Type      {d['fstype']}", ""
            ]

        io = get_io()
        if io:
            lines += [
                f"Read      {self.bytes(io.read_bytes)}",
                f"Write     {self.bytes(io.write_bytes)}"
            ]

        devices = get_devices()
        if devices:
            lines.append("\nBLOCK DEVICES")
            lines += [
                f"{d.get('path', d.get('name', '?')):16} "
                f"{d.get('size', '?'):>9} {d.get('type', '?'):6} "
                f"{d.get('model') or ''}"
                for d in devices
            ]

        self.set("disk", "\n".join(lines))

    def update_network(self):
        n = get_network()
        total = n["total"]
        now = time.monotonic()

        if self._net is None:
            self._net, self._net_t = total, now

        dt = max(now - self._net_t, 0.001)
        rx = (total.bytes_recv - self._net.bytes_recv) / dt
        tx = (total.bytes_sent - self._net.bytes_sent) / dt
        self._net, self._net_t = total, now

        lines = [
            f"Download   {self.bytes(rx)}/s",
            f"Upload     {self.bytes(tx)}/s", "",
            f"Total RX   {self.bytes(total.bytes_recv)}",
            f"Total TX   {self.bytes(total.bytes_sent)}", "",
            f"Packets RX {total.packets_recv:,}",
            f"Packets TX {total.packets_sent:,}",
            f"Errors RX  {total.errin:,}",
            f"Errors TX  {total.errout:,}", ""
        ]
        lines += [
            f"{name[:12]:12} ↓{self.bytes(i.bytes_recv)} ↑{self.bytes(i.bytes_sent)}"
            for name, i in n["interfaces"].items()
        ]
        lines += ["", f"Connections {len(n['connections'])}"]
        self.set("network", "\n".join(lines))

    def update_processes(self):
        processes = get_processes()[:25]
        lines = [
            "PID       PROCESS                       CPU      RAM       MEMORY       STATUS"
        ]
        lines += [
            f"{p['pid']:<9}{p['name'][:28]:<29}{p['cpu']:>5.1f}%   "
            f"{p['ram']:>5.1f}%   {self.bytes(p['memory']):>10}   {p['status']}"
            for p in processes
        ]
        self.set("processes", "\n".join(lines))

    def update_sensors(self):
        s, lines = get_sensors(), []
        for chip, items in s["temperatures"].items():
            lines.append(chip)
            for x in items:
                high = f"  high {x['high']:.1f}°C" if x["high"] else ""
                lines.append(
                    f"  {x['label'] or '?':20} {x['current']:6.1f}°C{high}"
                )
        for items in s["fans"].values():
            for x in items:
                lines.append(
                    f"  FAN {x['label'] or '?':16} {x['current']:6.0f} RPM"
                )
        self.set("sensors", "\n".join(lines) or "No sensors found.")

    def update_services(self):
        lines = [
            f"{s['name']:<40} {s['active']:<8} "
            f"{s['sub']:<10} {s['description']}"
            for s in get_services()[:100]
        ]
        self.set("services", "\n".join(lines) or "No services found.")

    def update_filesystem(self):
        lines = [
            f"{f['mount']:<25} {f['fstype']:<8} "
            f"{self.bar(f['percent'], 16)} {f['percent']:5.1f}% "
            f"{self.bytes(f['free'])} free"
            for f in get_filesystems()
        ]
        self.set("filesystem", "\n".join(lines) or "No filesystems.")

    def update_usb(self):
        lines = [
            f"{d['bus']}:{d['device']}  {d['id']}  {d['name']}"
            for d in get_usb()
        ]
        self.set("usb", "\n".join(lines) or "No USB devices.")

    def update_pci(self):
        lines = [
            f"{d['slot']:<15} {d['class']:<25} "
            f"{d['vendor']} {d['device']}"
            for d in get_pci()
        ]
        self.set("pci", "\n".join(lines) or "No PCI devices.")

    def update_battery(self):
        b = get_battery()
        if not b:
            self.set("battery", "No battery detected.")
            return
        self.set(
            "battery",
            f"Charge    {b['percent']:.1f}%\n{self.bar(b['percent'])}\n"
            f"Status    {'Charging / AC' if b['plugged'] else 'Discharging'}\n"
            f"Time      {self.seconds(b['seconds_left'])}"
        )

    def update_audio(self):
        self.set("audio", "\n".join(get_audio()) or "No audio information.")

    def update_bluetooth(self):
        lines = [f"{d['mac']:<18} {d['name']}" for d in get_bluetooth()]
        self.set("bluetooth", "\n".join(lines) or "No Bluetooth devices.")

    def update_wifi(self):
        lines = []
        for i in get_wifi():
            lines.append(
                f"{i['name']:<12} "
                f"{'CONNECTED' if i['connected'] else 'DISCONNECTED'}"
            )
            if i.get("link"):
                lines.append(f"  {i['link']}")
        self.set("wifi", "\n".join(lines) or "No Wi-Fi interfaces.")

    def update_users(self):
        lines = [
            f"{u['name']:<20} {str(u['terminal']):<10} "
            f"{str(u['host']):<20} PID {u['pid']}"
            for u in get_users()
        ]
        self.set("users", "\n".join(lines) or "No logged-in users.")

    def update_logs(self):
        self.set("logs", "\n".join(get_logs(20)) or "No logs.")

    def update_kernel(self):
        k = get_kernel()
        self.set(
            "kernel",
            f"Release       {k['release']}\nVersion       {k['version']}\n"
            f"Machine       {k['machine']}\nCommand line  {k['cmdline']}\n\n"
            f"Loaded modules: {len(k['modules'])}"
        )

    def update_process_tree(self):
        tree, lines = get_process_tree(), []
        for pid, children in tree.items():
            if children:
                names = ", ".join(
                    f"{x['name']}({x['pid']})" for x in children[:8]
                )
                lines.append(f"{pid:<8} → {names}")
        self.set("process_tree", "\n".join(lines[:80]) or "No process tree.")

    def update_containers(self):
        lines = [
            f"{c['id'][:12]:12} {c['name']:<20} "
            f"{c['status']:<25} {c['image']}"
            for c in get_containers()
        ]
        self.set("containers", "\n".join(lines) or "No containers.")

    def update_virtualization(self):
        v = get_virtualization()
        self.set(
            "virtualization",
            f"Virtualization  {v['virtualization']}\n"
            f"KVM             {'available' if v['kvm'] else 'unavailable'}\n"
            f"Hypervisor      {'present' if v['hypervisor'] else 'not detected'}"
        )

    def update_packages(self):
        p = get_packages()
        self.set(
            "packages",
            f"Manager   {p['manager'] or 'none'}\n"
            f"Packages  {len(p['packages']):,}\n\n"
            + "\n".join(p["packages"][:50])
        )

    def update_mounts(self):
        lines = [
            f"{m['device']:<25} {m['mount']:<30} "
            f"{m['fstype']:<10} {m['options']}"
            for m in get_mounts()
        ]
        self.set("mounts", "\n".join(lines) or "No mounts.")

    def update_cron(self):
        timers, cron = get_timers(), get_crontab()
        if not timers and not cron:
            self.set("cron", "No timers or crontab.")
            return
        self.set(
            "cron",
            "SYSTEMD TIMERS\n" + "\n".join(timers[:30]) +
            "\n\nCRONTAB\n" + "\n".join(cron)
        )

    def update_gpu_processes(self):
        lines = [
            f"{p['pid']:<8} {p['name']:<35} {p['vram']:>8} MiB"
            for p in get_gpu_processes()
        ]
        self.set("gpu_processes", "\n".join(lines) or "No GPU processes.")

    def update_ai(self):
        lines = [
            f"{p['pid']:<8} {p['name']:<20} "
            f"CPU {p['cpu']:5.1f}%  RAM {self.bytes(p['memory'])}"
            for p in get_ai_processes()
        ]
        self.set("ai", "\n".join(lines) or "No AI processes detected.")

    def update_ollama(self):
        lines = [
            f"{m.get('name', '?'):<35} {m.get('size', '?')} "
            f"{m.get('expires_at', '')}"
            for m in get_ollama()
        ]
        self.set("ollama", "\n".join(lines) or "Ollama is not running.")

    def update_cuda(self):
        cuda = get_cuda()
        if not cuda:
            self.set("cuda", "NVIDIA CUDA unavailable.")
            return
        self.set(
            "cuda",
            "\n".join(
                f"{g['name']}\nDriver    {g['driver']}\nCUDA      {g['cuda']}"
                for g in cuda
            )
        )

    def update_pytorch(self):
        p = get_pytorch()
        lines = [
            f"PyTorch   {p['version'] or 'not installed'}",
            f"CUDA      {p['cuda'] or 'none'}",
            f"Available {'YES' if p['available'] else 'NO'}"
        ]
        for g in p["gpus"]:
            lines += [
                "", f"GPU {g['index']}  {g['name']}",
                f"VRAM      {self.bytes(g['memory'])}"
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

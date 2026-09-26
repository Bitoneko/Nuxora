import os
import time
import platform
import psutil
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable


class Nuxora(App):
    TITLE = "Nuxora"
    SUB_TITLE = "Real-time Linux System Monitor"

    CSS = """
    Screen {
        background: $background;
    }

    #main {
        height: 1fr;
        padding: 0 1;
    }

    .row {
        height: 1fr;
    }

    .panel {
        border: solid $accent;
        padding: 0 1;
        margin: 0 1 1 0;
        height: 1fr;
    }

    .wide {
        width: 2fr;
    }

    .narrow {
        width: 1fr;
    }

    .full {
        width: 1fr;
        height: 2fr;
    }

    Static {
        height: auto;
    }

    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="main"):
            with Horizontal(classes="row"):
                yield Static(id="system", classes="panel narrow")
                yield Static(id="cpu", classes="panel wide")
                yield Static(id="memory", classes="panel wide")

            with Horizontal(classes="row"):
                yield Static(id="gpu", classes="panel wide")
                yield Static(id="disk", classes="panel wide")
                yield Static(id="network", classes="panel wide")

            with Vertical(classes="panel full"):
                yield Static("Processes")
                yield DataTable(id="processes")

        yield Footer()

    def on_mount(self):
        table = self.query_one("#processes", DataTable)

        table.add_columns(
            "PID",
            "Process",
            "CPU %",
            "Memory %",
            "Memory",
            "Status",
        )

        self.update_all()
        self.set_interval(1, self.update_all)

    def update_all(self):
        self.update_system()
        self.update_cpu()
        self.update_memory()
        self.update_gpu()
        self.update_disk()
        self.update_network()
        self.update_processes()

    def update_system(self):
        uptime = time.time() - psutil.boot_time()

        days = int(uptime // 86400)
        hours = int((uptime % 86400) // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)

        text = (
            "[bold]SYSTEM[/bold]\n\n"
            f"OS       {platform.system()} {platform.release()}\n"
            f"Machine  {platform.machine()}\n"
            f"Hostname {platform.node()}\n"
            f"Uptime   {days}d {hours:02d}:{minutes:02d}:{seconds:02d}\n"
            f"Time     {datetime.now().strftime('%H:%M:%S')}\n"
            f"Users    {len(psutil.users())}"
        )

        self.query_one("#system", Static).update(text)

    def update_cpu(self):
        total = psutil.cpu_percent()
        cores = psutil.cpu_percent(percpu=True)
        freq = psutil.cpu_freq()

        lines = [
            "[bold]CPU[/bold]",
            "",
            f"Total      {total:5.1f}%",
        ]

        if freq:
            lines.append(f"Frequency  {freq.current:5.0f} MHz")

        lines.append(f"Cores      {len(cores)}")
        lines.append("")

        for i, usage in enumerate(cores):
            bars = self.bar(usage)
            lines.append(f"{i:02d} {bars} {usage:5.1f}%")

        load = os.getloadavg() if hasattr(os, "getloadavg") else None

        if load:
            lines.extend([
                "",
                f"Load       {load[0]:.2f} {load[1]:.2f} {load[2]:.2f}",
            ])

        self.query_one("#cpu", Static).update("\n".join(lines))

    def update_memory(self):
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        text = (
            "[bold]MEMORY[/bold]\n\n"
            f"RAM        {self.bytes(memory.used)} / "
            f"{self.bytes(memory.total)}\n"
            f"Usage      {memory.percent:.1f}%\n"
            f"Available  {self.bytes(memory.available)}\n"
            f"Cached     {self.bytes(getattr(memory, 'cached', 0))}\n\n"
            f"SWAP       {self.bytes(swap.used)} / "
            f"{self.bytes(swap.total)}\n"
            f"Usage      {swap.percent:.1f}%\n\n"
            f"{self.bar(memory.percent)}"
        )

        self.query_one("#memory", Static).update(text)

    def update_gpu(self):
        try:
            import pynvml

            pynvml.nvmlInit()

            count = pynvml.nvmlDeviceGetCount()

            lines = ["[bold]GPU[/bold]", ""]

            for i in range(count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)

                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode()

                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                temperature = pynvml.nvmlDeviceGetTemperature(
                    handle,
                    pynvml.NVML_TEMPERATURE_GPU,
                )

                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000
                except Exception:
                    power = 0

                lines.extend([
                    f"{name}",
                    "",
                    f"GPU        {utilization.gpu:5.1f}%",
                    f"VRAM       {self.bytes(memory.used)} / "
                    f"{self.bytes(memory.total)}",
                    f"VRAM       {memory.used / memory.total * 100:5.1f}%",
                    f"Temperature {temperature}°C",
                    f"Power      {power:.1f} W",
                ])

                if i < count - 1:
                    lines.append("")

            self.query_one("#gpu", Static).update("\n".join(lines))

        except Exception:
            self.query_one("#gpu", Static).update(
                "[bold]GPU[/bold]\n\n"
                "NVIDIA GPU information unavailable.\n\n"
                "Install pynvml to enable GPU monitoring."
            )

    def update_disk(self):
        lines = ["[bold]DISK[/bold]", ""]

        partitions = psutil.disk_partitions(all=False)

        seen = set()

        for partition in partitions:
            mount = partition.mountpoint

            if mount in seen:
                continue

            seen.add(mount)

            try:
                usage = psutil.disk_usage(mount)
            except PermissionError:
                continue

            lines.extend([
                f"{mount}",
                f"{self.bar(usage.percent)} {usage.percent:.1f}%",
                f"{self.bytes(usage.used)} / {self.bytes(usage.total)}",
                "",
            ])

        self.query_one("#disk", Static).update("\n".join(lines))

    def update_network(self):
        current = psutil.net_io_counters()

        if not hasattr(self, "_last_net"):
            self._last_net = current
            self._last_net_time = time.monotonic()

        now = time.monotonic()
        elapsed = max(now - self._last_net_time, 0.001)

        rx = (current.bytes_recv - self._last_net.bytes_recv) / elapsed
        tx = (current.bytes_sent - self._last_net.bytes_sent) / elapsed

        self._last_net = current
        self._last_net_time = now

        text = (
            "[bold]NETWORK[/bold]\n\n"
            f"Download   {self.bytes(rx)}/s\n"
            f"Upload     {self.bytes(tx)}/s\n\n"
            f"Total RX   {self.bytes(current.bytes_recv)}\n"
            f"Total TX   {self.bytes(current.bytes_sent)}\n\n"
            f"Packets RX {current.packets_recv:,}\n"
            f"Packets TX {current.packets_sent:,}"
        )

        self.query_one("#network", Static).update(text)

    def update_processes(self):
        table = self.query_one("#processes", DataTable)

        processes = []

        for process in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent", "memory_info", "status"]
        ):
            try:
                info = process.info

                memory = info["memory_info"].rss if info["memory_info"] else 0

                processes.append(
                    (
                        info["cpu_percent"] or 0,
                        info["pid"],
                        info["name"] or "?",
                        info["memory_percent"] or 0,
                        memory,
                        info["status"] or "?",
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        processes.sort(reverse=True)

        table.clear()

        for cpu, pid, name, memory_percent, memory, status in processes[:20]:
            table.add_row(
                str(pid),
                name[:30],
                f"{cpu:.1f}",
                f"{memory_percent:.1f}",
                self.bytes(memory),
                status,
            )

    @staticmethod
    def bar(value, width=18):
        value = max(0, min(100, value))
        filled = int(width * value / 100)
        return "█" * filled + "░" * (width - filled)

    @staticmethod
    def bytes(value):
        value = float(value)

        units = ["B", "KB", "MB", "GB", "TB"]

        for unit in units:
            if abs(value) < 1024:
                return f"{value:.1f} {unit}"
            value /= 1024

        return f"{value:.1f} PB"


if __name__ == "__main__":
    Nuxora().run()

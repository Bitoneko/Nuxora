import os,time
from textual.app import App,ComposeResult
from textual.containers import Container,Horizontal,Vertical
from textual.widgets import Header,Footer,Static,DataTable
from .collectors.system import get_system
from .collectors.cpu import get_cpu
from .collectors.memory import get_memory
from .collectors.gpu import get_gpu
from .collectors.disks import get_disks,get_io,get_devices
from .collectors.network import get_network
from .collectors.processes import get_processes


class Nuxora(App):
    TITLE="Nuxora"
    SUB_TITLE="Real-time Linux System Monitor"
    CSS="""
    Screen{background:$background}
    #main{height:1fr;padding:0 1}
    .row{height:1fr}
    .panel{border:solid $accent;padding:0 1;margin:0 1 1 0;height:1fr;overflow:hidden}
    .wide{width:2fr}.narrow{width:1fr}.full{width:1fr;height:2fr}
    Static{height:auto}
    DataTable{height:1fr}
    """
    BINDINGS=[("q","quit","Quit"),("r","refresh","Refresh")]

    def compose(self)->ComposeResult:
        yield Header()
        with Container(id="main"):
            with Horizontal(classes="row"):
                yield Static(id="system",classes="panel narrow")
                yield Static(id="cpu",classes="panel wide")
                yield Static(id="memory",classes="panel wide")
            with Horizontal(classes="row"):
                yield Static(id="gpu",classes="panel wide")
                yield Static(id="disk",classes="panel wide")
                yield Static(id="network",classes="panel wide")
            with Vertical(classes="panel full"):
                yield Static("PROCESSES")
                yield DataTable(id="processes")
        yield Footer()

    def on_mount(self):
        self.table=self.query_one("#processes",DataTable)
        self.table.add_columns("PID","Process","CPU %","RAM %","Memory","Status")
        self.update_all()
        self.set_interval(1,self.update_all)

    def action_refresh(self):
        self.update_all()

    def update_all(self):
        self.update_system()
        self.update_cpu()
        self.update_memory()
        self.update_gpu()
        self.update_disk()
        self.update_network()
        self.update_processes()

    def update_system(self):
        s=get_system()
        battery="" if s.get("battery") is None else f"\nBattery   {s['battery']:.0f}%"+(" Charging" if s["charging"] else "")
        self.set("system",
            "[bold]SYSTEM[/bold]\n\n"
            f"OS        {s['os']}\n"
            f"Kernel    {s['kernel']}\n"
            f"Machine   {s['machine']}\n"
            f"Host      {s['host']}\n"
            f"Uptime    {s['uptime']}\n"
            f"Time      {s['time']}\n"
            f"Users     {s['users']}\n"
            f"Boot      {s['boot']}{battery}")

    def update_cpu(self):
        c=get_cpu();f=c["frequency"]
        lines=["[bold]CPU[/bold]","",f"Total     {c['total']:5.1f}%",
               f"Cores     {c['count']} ({c['physical']} physical)"]
        if f:
            lines += [f"Clock     {f.current:5.0f} MHz",f"Max       {f.max:5.0f} MHz"]
        lines += ["",*[f"{i:02d} {self.bar(v,14)} {v:5.1f}%" for i,v in enumerate(c["cores"])],
                  "",f"Load      {c['load'][0]:.2f} {c['load'][1]:.2f} {c['load'][2]:.2f}"]
        self.set("cpu","\n".join(lines))

    def update_memory(self):
        m=get_memory();r=m["ram"];s=m["swap"]
        self.set("memory",
            "[bold]MEMORY[/bold]\n\n"
            f"RAM       {self.bytes(r.used)} / {self.bytes(r.total)}\n"
            f"Usage     {r.percent:5.1f}%\n{self.bar(r.percent)}\n\n"
            f"Available {self.bytes(r.available)}\n"
            f"Cached    {self.bytes(getattr(r,'cached',0))}\n"
            f"Buffers   {self.bytes(getattr(r,'buffers',0))}\n"
            f"Shared    {self.bytes(getattr(r,'shared',0))}\n\n"
            f"SWAP      {self.bytes(s.used)} / {self.bytes(s.total)}\n"
            f"Usage     {s.percent:5.1f}%\n{self.bar(s.percent)}")

    def update_gpu(self):
        g=get_gpu()
        if not g:
            self.set("gpu","[bold]GPU[/bold]\n\nNVIDIA GPU unavailable.")
            return
        lines=["[bold]GPU[/bold]",""]
        for i,x in enumerate(g):
            p=x["vram_used"]/x["vram_total"]*100
            lines += [
                x["name"],"",
                f"GPU       {x['gpu']:5.1f}%",
                f"VRAM      {self.bytes(x['vram_used'])} / {self.bytes(x['vram_total'])}",
                f"Usage     {p:5.1f}%",
                self.bar(p),
                f"Temp      {x['temp']}°C",
                f"Power     {x['power']:.1f} W",
                f"Clock     {x['clock']} MHz",
                f"Mem Clock {x['memclock']} MHz"
            ]
            if x["fan"] is not None:
                lines.append(f"Fan       {x['fan']}%")
            if i<len(g)-1:
                lines.append("")
        self.set("gpu","\n".join(lines))

    def update_disk(self):
        lines=["[bold]DISK[/bold]",""]
        for d in get_disks():
            lines += [
                d["device"],d["mount"],
                f"{self.bar(d['percent'])} {d['percent']:5.1f}%",
                f"Used      {self.bytes(d['used'])}",
                f"Free      {self.bytes(d['free'])}",
                f"Total     {self.bytes(d['total'])}",
                f"Type      {d['fstype']}",""
            ]
        io=get_io()
        if io:
            lines += [f"Read      {self.bytes(io.read_bytes)}",
                      f"Write     {self.bytes(io.write_bytes)}"]
        devices=get_devices()
        if devices:
            lines += ["","[bold]BLOCK DEVICES[/bold]"]
            for d in devices:
                model=d.get("model") or ""
                lines.append(
                    f"{d.get('path',d.get('name','?')):16} "
                    f"{d.get('size','?'):>9} "
                    f"{d.get('type','?'):6} {model}"
                )
        self.set("disk","\n".join(lines))

    def update_network(self):
        n=get_network();c=n["total"];now=time.monotonic()
        if not hasattr(self,"_net"):
            self._net=c
            self._net_t=now
        dt=max(now-self._net_t,.001)
        rx=(c.bytes_recv-self._net.bytes_recv)/dt
        tx=(c.bytes_sent-self._net.bytes_sent)/dt
        self._net=c
        self._net_t=now
        lines=[
            "[bold]NETWORK[/bold]","",
            f"Download  {self.bytes(rx)}/s",
            f"Upload    {self.bytes(tx)}/s","",
            f"Total RX  {self.bytes(c.bytes_recv)}",
            f"Total TX  {self.bytes(c.bytes_sent)}","",
            f"Packets RX {c.packets_recv:,}",
            f"Packets TX {c.packets_sent:,}",
            f"Errors RX  {c.errin:,}",
            f"Errors TX  {c.errout:,}",""
        ]
        for name,v in n["interfaces"].items():
            lines.append(f"{name[:12]:12} ↓{self.bytes(v.bytes_recv)} ↑{self.bytes(v.bytes_sent)}")
        lines += ["",f"Connections {len(n['connections'])}"]
        self.set("network","\n".join(lines))

    def update_processes(self):
        self.table.clear()
        for p in get_processes()[:25]:
            self.table.add_row(
                str(p["pid"]),p["name"][:30],f"{p['cpu']:.1f}",
                f"{p['ram']:.1f}",self.bytes(p["memory"]),p["status"]
            )

    def set(self,id,text):
        self.query_one(f"#{id}",Static).update(text)

    @staticmethod
    def bar(v,width=18):
        v=max(0,min(100,v));n=int(width*v/100)
        return "█"*n+"░"*(width-n)

    @staticmethod
    def bytes(v):
        v=float(v)
        for u in ("B","KB","MB","GB","TB"):
            if abs(v)<1024:
                return f"{v:.1f} {u}"
            v/=1024
        return f"{v:.1f} PB"

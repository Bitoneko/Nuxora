import os,time,platform,psutil
from datetime import datetime
from textual.app import App,ComposeResult
from textual.containers import Container,Horizontal,Vertical
from textual.widgets import Header,Footer,Static,DataTable


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
        self.update_system();self.update_cpu();self.update_memory()
        self.update_gpu();self.update_disk();self.update_network();self.update_processes()

    def update_system(self):
        u=time.time()-psutil.boot_time()
        d,h=divmod(int(u),86400);h,m=divmod(h,3600);m,s=divmod(m,60)
        self.set("system",
            "[bold]SYSTEM[/bold]\n\n"
            f"OS        {platform.system()} {platform.release()}\n"
            f"Kernel    {platform.version().split('#')[0].strip()}\n"
            f"Machine   {platform.machine()}\n"
            f"Host      {platform.node()}\n"
            f"Uptime    {d}d {h:02d}:{m:02d}:{s:02d}\n"
            f"Time      {datetime.now():%H:%M:%S}\n"
            f"Users     {len(psutil.users())}\n"
            f"Boot      {datetime.fromtimestamp(psutil.boot_time()):%Y-%m-%d %H:%M}")

    def update_cpu(self):
        total=psutil.cpu_percent()
        cores=psutil.cpu_percent(percpu=True)
        freq=psutil.cpu_freq()
        load=os.getloadavg() if hasattr(os,"getloadavg") else (0,0,0)
        lines=["[bold]CPU[/bold]","",f"Total     {total:5.1f}%"]
        if freq: lines.append(f"Clock     {freq.current:5.0f} MHz")
        if freq and freq.max: lines.append(f"Max       {freq.max:5.0f} MHz")
        lines+= [f"Cores     {len(cores)}","",*[f"{i:02d} {self.bar(v,14)} {v:5.1f}%" for i,v in enumerate(cores)],
                 "",f"Load      {load[0]:.2f} {load[1]:.2f} {load[2]:.2f}"]
        self.set("cpu","\n".join(lines))

    def update_memory(self):
        m=psutil.virtual_memory();s=psutil.swap_memory()
        self.set("memory",
            "[bold]MEMORY[/bold]\n\n"
            f"RAM       {self.bytes(m.used)} / {self.bytes(m.total)}\n"
            f"Usage     {m.percent:5.1f}%\n"
            f"{self.bar(m.percent)}\n\n"
            f"Available {self.bytes(m.available)}\n"
            f"Cached    {self.bytes(getattr(m,'cached',0))}\n"
            f"Buffers   {self.bytes(getattr(m,'buffers',0))}\n\n"
            f"SWAP      {self.bytes(s.used)} / {self.bytes(s.total)}\n"
            f"Usage     {s.percent:5.1f}%\n"
            f"{self.bar(s.percent)}")

    def update_gpu(self):
        try:
            import pynvml as n
            if not hasattr(self,"_nvml"):
                n.nvmlInit();self._nvml=True
            lines=["[bold]GPU[/bold]",""]
            for i in range(n.nvmlDeviceGetCount()):
                h=n.nvmlDeviceGetHandleByIndex(i)
                name=n.nvmlDeviceGetName(h)
                name=name.decode() if isinstance(name,bytes) else name
                mem=n.nvmlDeviceGetMemoryInfo(h);u=n.nvmlDeviceGetUtilizationRates(h)
                temp=n.nvmlDeviceGetTemperature(h,n.NVML_TEMPERATURE_GPU)
                try: power=n.nvmlDeviceGetPowerUsage(h)/1000
                except: power=0
                try: clock=n.nvmlDeviceGetClockInfo(n.NVML_CLOCK_GRAPHICS,h)
                except: clock=0
                try: fan=n.nvmlDeviceGetFanSpeed(h)
                except: fan=None
                lines += [name,"",f"GPU       {u.gpu:5.1f}%",
                          f"VRAM      {self.bytes(mem.used)} / {self.bytes(mem.total)}",
                          f"Usage     {mem.used/mem.total*100:5.1f}%",
                          f"{self.bar(mem.used/mem.total*100)}",
                          f"Temp      {temp}°C",f"Power     {power:.1f} W",
                          f"Clock     {clock} MHz"]
                if fan is not None: lines.append(f"Fan       {fan}%")
                if i<n.nvmlDeviceGetCount()-1: lines.append("")
            self.set("gpu","\n".join(lines))
        except Exception:
            self.set("gpu","[bold]GPU[/bold]\n\nNVIDIA GPU unavailable.\n\nInstall pynvml.")

    def update_disk(self):
        lines=["[bold]DISK[/bold]",""]
        seen=set()
        for p in psutil.disk_partitions(False):
            if p.mountpoint in seen: continue
            seen.add(p.mountpoint)
            try: u=psutil.disk_usage(p.mountpoint)
            except: continue
            lines += [p.mountpoint,
                      f"{self.bar(u.percent)} {u.percent:5.1f}%",
                      f"Used      {self.bytes(u.used)}",
                      f"Free      {self.bytes(u.free)}",
                      f"Total     {self.bytes(u.total)}",""]
        io=psutil.disk_io_counters()
        if io: lines += [f"Read      {self.bytes(io.read_bytes)}",f"Write     {self.bytes(io.write_bytes)}"]
        self.set("disk","\n".join(lines))

    def update_network(self):
        c=psutil.net_io_counters();now=time.monotonic()
        if not hasattr(self,"_net"): self._net=c;self._net_t=now
        dt=max(now-self._net_t,.001)
        rx=(c.bytes_recv-self._net.bytes_recv)/dt
        tx=(c.bytes_sent-self._net.bytes_sent)/dt
        self._net=c;self._net_t=now
        self.set("network",
            "[bold]NETWORK[/bold]\n\n"
            f"Download  {self.bytes(rx)}/s\n"
            f"Upload    {self.bytes(tx)}/s\n\n"
            f"Total RX  {self.bytes(c.bytes_recv)}\n"
            f"Total TX  {self.bytes(c.bytes_sent)}\n\n"
            f"Packets RX {c.packets_recv:,}\n"
            f"Packets TX {c.packets_sent:,}\n"
            f"Errors RX  {c.errin:,}\n"
            f"Errors TX  {c.errout:,}")

    def update_processes(self):
        data=[]
        for p in psutil.process_iter(["pid","name","cpu_percent","memory_percent","memory_info","status"]):
            try:
                i=p.info;m=i["memory_info"]
                data.append((i["cpu_percent"] or 0,i["pid"],i["name"] or "?",i["memory_percent"] or 0,
                             m.rss if m else 0,i["status"] or "?"))
            except (psutil.NoSuchProcess,psutil.AccessDenied): pass
        data.sort(key=lambda x:x[0],reverse=True)
        self.table.clear()
        for cpu,pid,name,ram,mem,status in data[:25]:
            self.table.add_row(str(pid),name[:30],f"{cpu:.1f}",f"{ram:.1f}",self.bytes(mem),status)

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
            if abs(v)<1024:return f"{v:.1f} {u}"
            v/=1024
        return f"{v:.1f} PB"


if __name__=="__main__":
    Nuxora().run()

import json
import os
import time
from textual.app import App,ComposeResult
from textual.containers import Container,Horizontal,Vertical,ScrollableContainer
from textual.widgets import Header,Footer,Static,DataTable,Checkbox,Button
from textual.screen import ModalScreen

from collectors.system import get_system
from collectors.cpu import get_cpu
from collectors.memory import get_memory
from collectors.gpu import get_gpu
from collectors.disks import get_disks,get_io,get_devices
from collectors.network import get_network
from collectors.processes import get_processes
from collectors.sensors import get_sensors
from collectors.services import get_services
from collectors.filesystem import get_filesystems
from collectors.usb import get_usb
from collectors.pci import get_pci
from collectors.battery import get_battery
from collectors.audio import get_audio
from collectors.bluetooth import get_bluetooth
from collectors.wifi import get_wifi
from collectors.users import get_users
from collectors.logs import get_logs
from collectors.kernel import get_kernel
from collectors.processes_tree import get_process_tree
from collectors.containers import get_containers
from collectors.virtualization import get_virtualization
from collectors.packages import get_packages
from collectors.mounts import get_mounts
from collectors.cron import get_timers,get_crontab
from collectors.gpu_processes import get_gpu_processes
from collectors.ai import get_ai_processes
from collectors.ollama import get_ollama
from collectors.cuda import get_cuda
from collectors.pytorch import get_pytorch


class SettingsScreen(ModalScreen):
    CSS="""
    SettingsScreen{align:center middle;background:rgba(0,0,0,.7)}
    #settings{width:60%;height:80%;border:solid $accent;background:$surface;padding:1 2}
    #settings-title{height:3;text-style:bold}
    #checks{height:1fr;overflow:auto}
    #buttons{height:3;align:right middle}
    Button{margin-left:1}
    """

    def __init__(self,app):
        super().__init__()
        self.main_app=app

    def compose(self):
        with Vertical(id="settings"):
            yield Static("NUXORA DISPLAY SETTINGS",id="settings-title")
            with ScrollableContainer(id="checks"):
                for key,name in self.main_app.collectors:
                    yield Checkbox(name,value=self.main_app.visible.get(key,True),id=f"check-{key}")
            with Horizontal(id="buttons"):
                yield Button("Apply",variant="primary",id="apply")
                yield Button("Cancel",id="cancel")

    def on_button_pressed(self,event):
        if event.button.id=="cancel":
            self.dismiss()
            return
        for key,_ in self.main_app.collectors:
            box=self.query_one(f"#check-{key}",Checkbox)
            self.main_app.visible[key]=box.value
            self.main_app.set_panel_visible(key,box.value)
        self.main_app.save_visibility()
        self.dismiss()


class Nuxora(App):
    TITLE="Nuxora"
    SUB_TITLE="Real-time Linux System Monitor"
    CSS="""
    Screen{background:$background}
    #main{height:1fr;padding:0 1}
    #dashboard{height:1fr}
    .panel{border:solid $accent;padding:0 1;margin:0 1 1 0;min-height:12}
    .wide{width:1fr}
    .full{width:1fr}
    .title{height:2;text-style:bold;color:$accent}
    Static{height:auto}
    DataTable{height:1fr}
    """

    BINDINGS=[
        ("q","quit","Quit"),
        ("r","refresh","Refresh"),
        ("ctrl+p","settings","Settings")
    ]

    collectors=[
        ("system","System"),
        ("cpu","CPU"),
        ("memory","Memory"),
        ("gpu","GPU"),
        ("disk","Disk"),
        ("network","Network"),
        ("processes","Processes"),
        ("sensors","Sensors"),
        ("services","Services"),
        ("filesystem","Filesystem"),
        ("usb","USB"),
        ("pci","PCI"),
        ("battery","Battery"),
        ("audio","Audio"),
        ("bluetooth","Bluetooth"),
        ("wifi","Wi-Fi"),
        ("users","Users"),
        ("logs","Logs"),
        ("kernel","Kernel"),
        ("process_tree","Process Tree"),
        ("containers","Containers"),
        ("virtualization","Virtualization"),
        ("packages","Packages"),
        ("mounts","Mounts"),
        ("cron","Cron / Timers"),
        ("gpu_processes","GPU Processes"),
        ("ai","AI Processes"),
        ("ollama","Ollama"),
        ("cuda","CUDA"),
        ("pytorch","PyTorch")
    ]

    def __init__(self):
        super().__init__()
        self.config_path=os.path.expanduser("~/.config/nuxora/visibility.json")
        self.visible=self.load_visibility()

    def compose(self)->ComposeResult:
        yield Header()
        with ScrollableContainer(id="dashboard"):
            for key,name in self.collectors:
                yield Vertical(
                    Static(name.upper(),classes="title"),
                    Static(id=f"panel-{key}"),
                    classes="panel wide"
                )
        yield Footer()

    def on_mount(self):
        for key,_ in self.collectors:
            self.set_panel_visible(key,self.visible.get(key,True))
        self.update_all()
        self.set_interval(1,self.update_all)

    def action_refresh(self):
        self.update_all()

    def action_settings(self):
        self.push_screen(SettingsScreen(self))

    def load_visibility(self):
        default={k:True for k,_ in self.collectors}
        try:
            with open(self.config_path) as f:
                default.update(json.load(f))
        except Exception:
            pass
        return default

    def save_visibility(self):
        os.makedirs(os.path.dirname(self.config_path),exist_ok=True)
        with open(self.config_path,"w") as f:
            json.dump(self.visible,f,indent=2)

    def set_panel_visible(self,key,value):
        try:
            self.query_one(f"#panel-{key}").display=value
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

    def set(self,key,text):
        self.query_one(f"#panel-{key}",Static).update(text)

    def update_system(self):
        s=get_system()
        b="" if s.get("battery") is None else f"\nBattery   {s['battery']:.0f}%"+(" Charging" if s["charging"] else "")
        self.set("system",
            f"OS        {s['os']}\n"
            f"Kernel    {s['kernel']}\n"
            f"Machine   {s['machine']}\n"
            f"Host      {s['host']}\n"
            f"Uptime    {s['uptime']}\n"
            f"Time      {s['time']}\n"
            f"Users     {s['users']}\n"
            f"Boot      {s['boot']}{b}")

    def update_cpu(self):
        c=get_cpu();f=c["frequency"]
        x=[f"Total     {c['total']:5.1f}%",f"Cores     {c['count']} ({c['physical']} physical)"]
        if f:x += [f"Clock     {f.current:5.0f} MHz",f"Max       {f.max:5.0f} MHz"]
        x += ["",*[f"{i:02d} {self.bar(v,20)} {v:5.1f}%" for i,v in enumerate(c["cores"])],
              "",f"Load      {c['load'][0]:.2f} {c['load'][1]:.2f} {c['load'][2]:.2f}"]
        self.set("cpu","\n".join(x))

    def update_memory(self):
        m=get_memory();r=m["ram"];s=m["swap"]
        self.set("memory",
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
            self.set("gpu","NVIDIA GPU unavailable.")
            return
        x=[]
        for i,d in enumerate(g):
            p=d["vram_used"]/d["vram_total"]*100 if d["vram_total"] else 0
            x += [d["name"],f"GPU       {d['gpu']:5.1f}%",
                  f"VRAM      {self.bytes(d['vram_used'])} / {self.bytes(d['vram_total'])}",
                  f"Usage     {p:5.1f}%\n{self.bar(p)}",
                  f"Temp      {d['temp']}°C",f"Power     {d['power']:.1f} W",
                  f"Clock     {d['clock']} MHz",f"Mem Clock {d['memclock']} MHz"]
            if d["fan"] is not None:x.append(f"Fan       {d['fan']}%")
            if i<len(g)-1:x.append("")
        self.set("gpu","\n".join(x))

    def update_disk(self):
        x=[]
        for d in get_disks():
            x += [d["device"],d["mount"],f"{self.bar(d['percent'])} {d['percent']:5.1f}%",
                  f"Used      {self.bytes(d['used'])}",f"Free      {self.bytes(d['free'])}",
                  f"Total     {self.bytes(d['total'])}",f"Type      {d['fstype']}",""]
        io=get_io()
        if io:x += [f"Read      {self.bytes(io.read_bytes)}",f"Write     {self.bytes(io.write_bytes)}"]
        dev=get_devices()
        if dev:
            x += ["","BLOCK DEVICES"]
            for d in dev:
                x.append(f"{d.get('path',d.get('name','?')):16} {d.get('size','?'):>9} {d.get('type','?'):6} {d.get('model') or ''}")
        self.set("disk","\n".join(x))

    def update_network(self):
        n=get_network();c=n["total"];now=time.monotonic()
        if not hasattr(self,"_net"):
            self._net=c;self._net_t=now
        dt=max(now-self._net_t,.001)
        rx=(c.bytes_recv-self._net.bytes_recv)/dt
        tx=(c.bytes_sent-self._net.bytes_sent)/dt
        self._net=c;self._net_t=now
        x=[f"Download  {self.bytes(rx)}/s",f"Upload    {self.bytes(tx)}/s","",
           f"Total RX  {self.bytes(c.bytes_recv)}",f"Total TX  {self.bytes(c.bytes_sent)}","",
           f"Packets RX {c.packets_recv:,}",f"Packets TX {c.packets_sent:,}",
           f"Errors RX  {c.errin:,}",f"Errors TX  {c.errout:,}",""]
        for name,v in n["interfaces"].items():
            x.append(f"{name[:12]:12} ↓{self.bytes(v.bytes_recv)} ↑{self.bytes(v.bytes_sent)}")
        x += ["",f"Connections {len(n['connections'])}"]
        self.set("network","\n".join(x))

    def update_processes(self):
        p=get_processes()[:25]
        x=["PID       PROCESS                       CPU      RAM       MEMORY       STATUS"]
        x += [f"{d['pid']:<9}{d['name'][:28]:<29}{d['cpu']:>5.1f}%   {d['ram']:>5.1f}%   {self.bytes(d['memory']):>10}   {d['status']}" for d in p]
        self.set("processes","\n".join(x))

    def update_sensors(self):
        s=get_sensors();x=[]
        for chip,items in s["temperatures"].items():
            x.append(chip)
            for d in items:
                x.append(f"  {d['label'] or '?':20} {d['current']:6.1f}°C"+(f"  high {d['high']:.1f}°C" if d["high"] else ""))
        for chip,items in s["fans"].items():
            for d in items:x.append(f"  FAN {d['label'] or '?':16} {d['current']:6.0f} RPM")
        self.set("sensors","\n".join(x) or "No sensors found.")

    def update_services(self):
        s=get_services()
        x=[f"{d['name']:<40} {d['active']:<8} {d['sub']:<10} {d['description']}" for d in s]
        self.set("services","\n".join(x) or "No services found.")

    def update_filesystem(self):
        x=[]
        for d in get_filesystems():
            x.append(f"{d['mount']:<25} {d['fstype']:<8} {self.bar(d['percent'],16)} {d['percent']:5.1f}%  {self.bytes(d['free'])} free")
        self.set("filesystem","\n".join(x) or "No filesystems.")

    def update_usb(self):
        x=[f"{d['bus']}:{d['device']}  {d['id']}  {d['name']}" for d in get_usb()]
        self.set("usb","\n".join(x) or "No USB devices.")

    def update_pci(self):
        x=[f"{d['slot']:<15} {d['class']:<25} {d['vendor']} {d['device']}" for d in get_pci()]
        self.set("pci","\n".join(x) or "No PCI devices.")

    def update_battery(self):
        b=get_battery()
        self.set("battery","No battery detected." if not b else
                 f"Charge    {b['percent']:.1f}%\n{self.bar(b['percent'])}\n"
                 f"Status    {'Charging / AC' if b['plugged'] else 'Discharging'}\n"
                 f"Time      {self.seconds(b['seconds_left'])}")

    def update_audio(self):
        self.set("audio","\n".join(get_audio()) or "No audio information.")

    def update_bluetooth(self):
        x=[f"{d['mac']:<18} {d['name']}" for d in get_bluetooth()]
        self.set("bluetooth","\n".join(x) or "No Bluetooth devices.")

    def update_wifi(self):
        x=[]
        for d in get_wifi():
            x.append(f"{d['name']:<12} {'CONNECTED' if d['connected'] else 'DISCONNECTED'}")
            if d.get("link"):x.append(f"  {d['link']}")
        self.set("wifi","\n".join(x) or "No Wi-Fi interfaces.")

    def update_users(self):
        x=[f"{d['name']:<20} {str(d['terminal']):<10} {str(d['host']):<20} PID {d['pid']}" for d in get_users()]
        self.set("users","\n".join(x) or "No logged-in users.")

    def update_logs(self):
        self.set("logs","\n".join(get_logs(20)) or "No logs.")

    def update_kernel(self):
        k=get_kernel()
        x=[f"Release       {k['release']}",f"Version       {k['version']}",
           f"Machine       {k['machine']}",f"Command line  {k['cmdline']}","",
           f"Loaded modules: {len(k['modules'])}"]
        self.set("kernel","\n".join(x))

    def update_process_tree(self):
        t=get_process_tree();x=[]
        for pid,children in t.items():
            if not children:continue
            names=", ".join(f"{d['name']}({d['pid']})" for d in children[:8])
            x.append(f"{pid:<8} → {names}")
        self.set("process_tree","\n".join(x[:80]) or "No process tree.")

    def update_containers(self):
        x=[f"{d['id'][:12]:12} {d['name']:<20} {d['status']:<25} {d['image']}" for d in get_containers()]
        self.set("containers","\n".join(x) or "No containers.")

    def update_virtualization(self):
        v=get_virtualization()
        self.set("virtualization",
                 f"Virtualization  {v['virtualization']}\n"
                 f"KVM             {'available' if v['kvm'] else 'unavailable'}\n"
                 f"Hypervisor      {'present' if v['hypervisor'] else 'not detected'}")

    def update_packages(self):
        p=get_packages()
        self.set("packages",f"Manager   {p['manager'] or 'none'}\nPackages  {len(p['packages']):,}\n\n"+"\n".join(p["packages"][:50]))

    def update_mounts(self):
        x=[f"{d['device']:<25} {d['mount']:<30} {d['fstype']:<10} {d['options']}" for d in get_mounts()]
        self.set("mounts","\n".join(x) or "No mounts.")

    def update_cron(self):
        t=get_timers();c=get_crontab()
        self.set("cron","SYSTEMD TIMERS\n"+"\n".join(t[:30])+"\n\nCRONTAB\n"+"\n".join(c) if t or c else "No timers or crontab.")

    def update_gpu_processes(self):
        x=[f"{d['pid']:<8} {d['name']:<35} {d['vram']:>8} MiB" for d in get_gpu_processes()]
        self.set("gpu_processes","\n".join(x) or "No GPU processes.")

    def update_ai(self):
        x=[f"{d['pid']:<8} {d['name']:<20} CPU {d['cpu']:5.1f}%  RAM {self.bytes(d['memory'])}" for d in get_ai_processes()]
        self.set("ai","\n".join(x) or "No AI processes detected.")

    def update_ollama(self):
        x=[]
        for d in get_ollama():
            x.append(f"{d.get('name','?'):<35} {d.get('size','?')}  {d.get('expires_at','')}")
        self.set("ollama","\n".join(x) or "Ollama is not running.")

    def update_cuda(self):
        c=get_cuda()
        if not c:
            self.set("cuda","NVIDIA CUDA unavailable.")
            return
        self.set("cuda","\n".join(f"{d['name']}\nDriver    {d['driver']}\nCUDA      {d['cuda']}" for d in c))

    def update_pytorch(self):
        p=get_pytorch()
        x=[f"PyTorch   {p['version'] or 'not installed'}",
           f"CUDA      {p['cuda'] or 'none'}",
           f"Available {'YES' if p['available'] else 'NO'}"]
        for d in p["gpus"]:
            x += ["",f"GPU {d['index']}  {d['name']}",f"VRAM      {self.bytes(d['memory'])}"]
        self.set("pytorch","\n".join(x))

    @staticmethod
    def bar(v,width=18):
        v=max(0,min(100,float(v)));n=int(width*v/100)
        return "█"*n+"░"*(width-n)

    @staticmethod
    def bytes(v):
        v=float(v)
        for u in ("B","KB","MB","GB","TB"):
            if abs(v)<1024:return f"{v:.1f} {u}"
            v/=1024
        return f"{v:.1f} PB"

    @staticmethod
    def seconds(v):
        if v is None or v<0:return "Unknown"
        return time.strftime("%H:%M:%S",time.gmtime(v))


if __name__=="__main__":
    Nuxora().run()

import platform,time
from datetime import datetime
import psutil

def get_system():
    u=time.time()-psutil.boot_time()
    d,h=divmod(int(u),86400);h,m=divmod(h,3600);m,s=divmod(m,60)
    return {
        "os":f"{platform.system()} {platform.release()}",
        "kernel":platform.version().split("#")[0].strip(),
        "machine":platform.machine(),
        "host":platform.node(),
        "uptime":f"{d}d {h:02d}:{m:02d}:{s:02d}",
        "time":datetime.now().strftime("%H:%M:%S"),
        "users":len(psutil.users()),
        "boot":datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M")
    }
  

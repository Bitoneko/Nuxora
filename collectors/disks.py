import json,subprocess,psutil

def get_disks():
    result=[]
    for p in psutil.disk_partitions(all=True):
        try:
            u=psutil.disk_usage(p.mountpoint)
            result.append({
                "device":p.device,
                "mount":p.mountpoint,
                "fstype":p.fstype,
                "total":u.total,
                "used":u.used,
                "free":u.free,
                "percent":u.percent
            })
        except (PermissionError,OSError):
            pass
    return result

def get_io():
    return psutil.disk_io_counters()

def get_devices():
    try:
        r=subprocess.run(
            ["lsblk","-J","-o","NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,UUID,ROTA,RM"],
            capture_output=True,text=True,check=True
        )
        return json.loads(r.stdout).get("blockdevices",[])
    except (OSError,subprocess.SubprocessError,json.JSONDecodeError):
        return []

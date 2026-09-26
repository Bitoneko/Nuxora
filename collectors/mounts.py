import psutil

def get_mounts():
    return [
        {
            "device":p.device,
            "mount":p.mountpoint,
            "fstype":p.fstype,
            "options":p.opts
        }
        for p in psutil.disk_partitions(all=True)
    ]

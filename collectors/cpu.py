import os,psutil

def get_cpu():
    return {
        "total":psutil.cpu_percent(),
        "cores":psutil.cpu_percent(percpu=True),
        "frequency":psutil.cpu_freq(),
        "load":os.getloadavg() if hasattr(os,"getloadavg") else (0,0,0)
    }

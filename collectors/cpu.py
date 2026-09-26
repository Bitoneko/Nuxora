import os
import psutil

def get_cpu():
    return {
        "total": psutil.cpu_percent(),
        "count": psutil.cpu_count(logical=True) or 0,
        "physical": psutil.cpu_count(logical=False) or 0,
        "cores": psutil.cpu_percent(percpu=True),
        "frequency": psutil.cpu_freq(),
        "load": os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)
    }

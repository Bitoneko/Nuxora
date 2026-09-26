import os,platform,subprocess

def get_kernel():
    modules=[]
    try:
        modules=subprocess.run(["lsmod"],capture_output=True,text=True,timeout=3).stdout.splitlines()[1:]
    except Exception:pass
    return {
        "release":platform.release(),
        "version":platform.version(),
        "machine":platform.machine(),
        "cmdline":open("/proc/cmdline").read().strip() if os.path.exists("/proc/cmdline") else "",
        "modules":modules
    }

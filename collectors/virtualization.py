import os,subprocess

def get_virtualization():
    try:
        r=subprocess.run(["systemd-detect-virt"],capture_output=True,text=True,timeout=2)
        virt=r.stdout.strip() or "none"
    except Exception:virt="unknown"
    return {
        "virtualization":virt,
        "kvm":os.path.exists("/dev/kvm"),
        "hypervisor":os.path.exists("/sys/hypervisor")
    }

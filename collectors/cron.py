import subprocess

def get_timers():
    try:
        r=subprocess.run(
            ["systemctl","list-timers","--all","--no-legend","--no-pager"],
            capture_output=True,text=True,timeout=3
        )
        return r.stdout.splitlines()
    except Exception:return []

def get_crontab():
    try:
        r=subprocess.run(["crontab","-l"],capture_output=True,text=True,timeout=3)
        return r.stdout.splitlines() if r.returncode==0 else []
    except Exception:return []

import subprocess

def get_logs(lines=50,priority=None):
    try:
        cmd=["journalctl","-n",str(lines),"--no-pager","-o","short"]
        if priority:cmd+=["-p",priority]
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=5)
        return r.stdout.splitlines()
    except Exception:return []

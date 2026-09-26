import subprocess

def get_services():
    try:
        r=subprocess.run(
            ["systemctl","list-units","--type=service","--all","--no-legend","--no-pager"],
            capture_output=True,text=True,timeout=3
        )
        out=[]
        for line in r.stdout.splitlines():
            p=line.split(None,4)
            if len(p)>=4:
                out.append({"name":p[0],"load":p[1],"active":p[2],"sub":p[3],"description":p[4] if len(p)>4 else ""})
        return out
    except Exception:return []

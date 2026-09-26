import subprocess

def get_containers():
    for cmd in (["docker","ps","-a","--format","{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}"],
                ["podman","ps","-a","--format","{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}"]):
        try:
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=3)
            if r.returncode==0:
                return [{"id":p[0],"name":p[1],"status":p[2],"image":p[3]} for x in r.stdout.splitlines() if len(p:=x.split("\t"))>=4]
        except Exception:pass
    return []

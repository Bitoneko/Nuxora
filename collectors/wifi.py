import subprocess

def get_wifi():
    try:
        r=subprocess.run(
            ["iw","dev"],capture_output=True,text=True,timeout=3
        )
        interfaces=[]
        for line in r.stdout.splitlines():
            s=line.strip()
            if s.startswith("Interface "):
                interfaces.append({"name":s.split()[1]})
        for x in interfaces:
            try:
                q=subprocess.run(["iw","dev",x["name"],"link"],capture_output=True,text=True,timeout=2)
                x["link"]=q.stdout.strip()
                x["connected"]="Connected to" in q.stdout
            except Exception:
                x["link"]="";x["connected"]=False
        return interfaces
    except Exception:return []

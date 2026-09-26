import subprocess

def get_usb():
    try:
        r=subprocess.run(["lsusb"],capture_output=True,text=True,timeout=3)
        out=[]
        for line in r.stdout.splitlines():
            p=line.split(None,6)
            if len(p)>=6:
                out.append({"bus":p[1],"device":p[3].rstrip(":"),"id":p[5],"name":p[6] if len(p)>6 else ""})
        return out
    except Exception:return []

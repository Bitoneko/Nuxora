import subprocess

def get_bluetooth():
    try:
        r=subprocess.run(["bluetoothctl","devices"],capture_output=True,text=True,timeout=3)
        out=[]
        for x in r.stdout.splitlines():
            p=x.split(None,2)
            if len(p)>=3:out.append({"mac":p[1],"name":p[2]})
        return out
    except Exception:return []

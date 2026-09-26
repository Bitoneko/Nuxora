import subprocess

def get_pci():
    try:
        r=subprocess.run(["lspci","-mm"],capture_output=True,text=True,timeout=3)
        out=[]
        for line in r.stdout.splitlines():
            p=line.split('"')
            if len(p)>=7:
                out.append({"slot":p[0].strip(),"class":p[1],"vendor":p[3],"device":p[5]})
        return out
    except Exception:return []

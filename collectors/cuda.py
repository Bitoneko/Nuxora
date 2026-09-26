import subprocess

def get_cuda():
    try:
        r=subprocess.run(["nvidia-smi"],capture_output=True,text=True,timeout=3)
        if r.returncode!=0:return None
        q=subprocess.run(
            ["nvidia-smi","--query-gpu=name,driver_version,cuda_version",
             "--format=csv,noheader"],
            capture_output=True,text=True,timeout=3
        )
        out=[]
        for x in q.stdout.splitlines():
            p=[v.strip() for v in x.split(",")]
            if len(p)>=3:out.append({"name":p[0],"driver":p[1],"cuda":p[2]})
        return out
    except Exception:return None

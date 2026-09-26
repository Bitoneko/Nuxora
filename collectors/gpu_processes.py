import subprocess

def get_gpu_processes():
    try:
        r=subprocess.run([
            "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits"
        ],capture_output=True,text=True,timeout=3)
        out=[]
        for x in r.stdout.splitlines():
            p=[v.strip() for v in x.split(",")]
            if len(p)>=3:out.append({"pid":int(p[0]),"name":p[1],"vram":int(p[2])})
        return out
    except Exception:return []

import os,subprocess,time

SCAN_ROOTS=[
    "/usr/local","/usr","/opt",
    "/mnt/data","/home","/root"
]

_cache=None
_cache_time=0


def _scan_cuda():
    global _cache,_cache_time

    now=time.monotonic()
    if _cache is not None and now-_cache_time<60:
        return _cache

    out=[]

    for root in SCAN_ROOTS:
        if not os.path.exists(root):
            continue

        try:
            for path,dirs,files in os.walk(root,topdown=True):
                lower=path.lower()

                if any(x in lower for x in (
                    "/proc/","/sys/","/dev/","/.git/",
                    "/node_modules/","/__pycache__/"
                )):
                    dirs[:]=[]
                    continue

                dirs[:]=[
                    d for d in dirs
                    if d not in {".git","__pycache__","node_modules",".venv","venv"}
                ]

                if any(x in lower for x in (
                    "/cuda","cuda-","/cudnn","cudatoolkit"
                )):
                    out.append(path)

                if len(out)>=200:
                    return out
        except (PermissionError,OSError):
            pass

    _cache=out
    _cache_time=now
    return out


def get_cuda():
    try:
        r=subprocess.run(
            ["nvidia-smi"],
            capture_output=True,text=True,timeout=3
        )

        if r.returncode!=0:
            return None

        q=subprocess.run(
            ["nvidia-smi",
             "--query-gpu=name,driver_version,cuda_version",
             "--format=csv,noheader"],
            capture_output=True,text=True,timeout=3
        )

        out=[]

        for x in q.stdout.splitlines():
            p=[v.strip() for v in x.split(",")]

            if len(p)>=3:
                out.append({
                    "name":p[0],
                    "driver":p[1],
                    "cuda":p[2]
                })

        paths=_scan_cuda()

        for gpu in out:
            gpu["paths"]=paths

        return out

    except Exception:
        return None
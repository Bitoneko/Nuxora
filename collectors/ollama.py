import json,os,time,urllib.request

_cache=[]
_cache_time=0


def _scan_models():
    global _cache,_cache_time

    now=time.monotonic()
    if now-_cache_time<60:
        return _cache

    out=[]

    for root in ["/mnt/data"]:
        if not os.path.exists(root):
            continue

        try:
            for path,dirs,files in os.walk(root,topdown=True):
                dirs[:]=[
                    d for d in dirs
                    if d not in {
                        ".git","__pycache__","node_modules",
                        ".venv","venv"
                    }
                ]

                if "ollama" not in path.lower():
                    dirs[:]=[
                        d for d in dirs
                        if "ollama" in d.lower()
                    ]

                for name in files:
                    if name!="manifest.json" and "ollama" not in path.lower():
                        continue

                    file_path=os.path.join(path,name)

                    try:
                        size=os.path.getsize(file_path)
                    except OSError:
                        size=0

                    out.append({
                        "name":name,
                        "path":file_path,
                        "size":size
                    })
        except (PermissionError,OSError):
            pass

    _cache=out
    _cache_time=now
    return out


def get_ollama():
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:11434/api/ps",timeout=2
        ) as r:
            return json.load(r).get("models",[])
    except Exception:
        pass

    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:11434/api/tags",timeout=2
        ) as r:
            return json.load(r).get("models",[])
    except Exception:
        pass

    return _scan_models()
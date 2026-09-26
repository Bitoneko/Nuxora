import os,time,psutil

MODEL_EXTENSIONS={
    ".safetensors",".ckpt",".pt",".pth",
    ".bin",".gguf",".ggml",".onnx",".sft"
}

SCAN_ROOTS=["/mnt/data"]
SKIP_DIRS={
    ".git","__pycache__","node_modules",
    ".venv","venv","site-packages"
}

_cache=[]
_cache_time=0


def _scan_models():
    global _cache,_cache_time

    now=time.monotonic()
    if now-_cache_time<60:
        return _cache

    out=[]

    for root in SCAN_ROOTS:
        if not os.path.exists(root):
            continue

        try:
            for path,dirs,files in os.walk(root,topdown=True):
                dirs[:]=[d for d in dirs if d not in SKIP_DIRS]

                for name in files:
                    if os.path.splitext(name)[1].lower() not in MODEL_EXTENSIONS:
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

    out.sort(key=lambda x:x["size"],reverse=True)
    _cache=out
    _cache_time=now
    return out


def get_ai_processes():
    keys=("python","python3","torch","ollama","stable","comfy","forge","cuda")
    out=[]

    for p in psutil.process_iter(
        ["pid","name","cmdline","cpu_percent","memory_info"]
    ):
        try:
            i=p.info
            text=" ".join(i["cmdline"] or []).lower()
            name=(i["name"] or "").lower()

            if any(k in name or k in text for k in keys):
                out.append({
                    "pid":i["pid"],
                    "name":i["name"] or "?",
                    "cpu":i["cpu_percent"] or 0,
                    "memory":i["memory_info"].rss if i["memory_info"] else 0,
                    "cmdline":text
                })
        except (psutil.NoSuchProcess,psutil.AccessDenied):
            pass

    return out


def get_ai_models():
    return _scan_models()
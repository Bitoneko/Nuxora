import os,time

MODEL_EXTENSIONS={
    ".pt",".pth",".ckpt",".safetensors",
    ".bin",".onnx",".gguf",".ggml"
}

_cache=None
_cache_time=0


def _scan_models():
    global _cache,_cache_time

    now=time.monotonic()
    if _cache is not None and now-_cache_time<60:
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
                        ".git","__pycache__","node_modules"
                    }
                ]

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


def get_pytorch():
    try:
        import torch

        out={
            "version":torch.__version__,
            "cuda":torch.version.cuda,
            "available":torch.cuda.is_available(),
            "gpus":[],
            "models":_scan_models()
        }

        if out["available"]:
            for i in range(torch.cuda.device_count()):
                out["gpus"].append({
                    "index":i,
                    "name":torch.cuda.get_device_name(i),
                    "memory":torch.cuda.get_device_properties(i).total_memory
                })

        return out

    except Exception:
        return {
            "version":None,
            "cuda":None,
            "available":False,
            "gpus":[],
            "models":_scan_models()
        }
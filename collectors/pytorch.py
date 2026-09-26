def get_pytorch():
    try:
        import torch
        out={"version":torch.__version__,"cuda":torch.version.cuda,"available":torch.cuda.is_available(),"gpus":[]}
        if out["available"]:
            for i in range(torch.cuda.device_count()):
                out["gpus"].append({
                    "index":i,
                    "name":torch.cuda.get_device_name(i),
                    "memory":torch.cuda.get_device_properties(i).total_memory
                })
        return out
    except Exception:return {"version":None,"cuda":None,"available":False,"gpus":[]}

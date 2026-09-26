def get_gpu():
    try:
        import pynvml as n
        if not hasattr(get_gpu,"nvml"):
            n.nvmlInit();get_gpu.nvml=True
        result=[]
        for i in range(n.nvmlDeviceGetCount()):
            h=n.nvmlDeviceGetHandleByIndex(i)
            name=n.nvmlDeviceGetName(h)
            name=name.decode() if isinstance(name,bytes) else name
            mem=n.nvmlDeviceGetMemoryInfo(h)
            u=n.nvmlDeviceGetUtilizationRates(h)
            try: temp=n.nvmlDeviceGetTemperature(h,n.NVML_TEMPERATURE_GPU)
            except: temp=0
            try: power=n.nvmlDeviceGetPowerUsage(h)/1000
            except: power=0
            try: clock=n.nvmlDeviceGetClockInfo(n.NVML_CLOCK_GRAPHICS,h)
            except: clock=0
            try: fan=n.nvmlDeviceGetFanSpeed(h)
            except: fan=None
            result.append({
                "name":name,"gpu":u.gpu,"vram_used":mem.used,
                "vram_total":mem.total,"temp":temp,"power":power,
                "clock":clock,"fan":fan
            })
        return result
    except Exception:
        return []

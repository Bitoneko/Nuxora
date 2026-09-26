def get_gpu():
    try:
        import pynvml as n

        if not hasattr(get_gpu, "nvml"):
            n.nvmlInit()
            get_gpu.nvml = True

        result = []

        for i in range(n.nvmlDeviceGetCount()):
            h = n.nvmlDeviceGetHandleByIndex(i)

            name = n.nvmlDeviceGetName(h)
            name = name.decode() if isinstance(name, bytes) else name

            mem = n.nvmlDeviceGetMemoryInfo(h)
            usage = n.nvmlDeviceGetUtilizationRates(h)

            try:
                temp = n.nvmlDeviceGetTemperature(
                    h, n.NVML_TEMPERATURE_GPU
                )
            except Exception:
                temp = 0

            try:
                power = n.nvmlDeviceGetPowerUsage(h) / 1000.0
                power_available = True
            except Exception:
                power = 0.0
                power_available = False

            try:
                clock = n.nvmlDeviceGetClockInfo(
                    h, n.NVML_CLOCK_GRAPHICS
                )
            except Exception:
                clock = 0

            try:
                memclock = n.nvmlDeviceGetClockInfo(
                    h, n.NVML_CLOCK_MEM
                )
            except Exception:
                memclock = 0

            try:
                fan = n.nvmlDeviceGetFanSpeed(h)
            except Exception:
                fan = 0

            result.append({
                "name": name,
                "gpu": usage.gpu,
                "vram_used": mem.used,
                "vram_total": mem.total,
                "temp": temp,
                "power": power,
                "power_available": power_available,
                "clock": clock,
                "memclock": memclock,
                "fan": fan
            })

        return result

    except Exception:
        return []

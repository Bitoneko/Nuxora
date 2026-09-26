def get_gpu():
    try:
        import pynvml as n

        if not hasattr(get_gpu, "nvml"):
            n.nvmlInit()
            get_gpu.nvml = True

        result = []

        count = n.nvmlDeviceGetCount()

        for i in range(count):
            h = n.nvmlDeviceGetHandleByIndex(i)

            name = n.nvmlDeviceGetName(h)
            if isinstance(name, bytes):
                name = name.decode(errors="replace")

            try:
                mem = n.nvmlDeviceGetMemoryInfo(h)
                vram_used = mem.used
                vram_total = mem.total
            except Exception:
                vram_used = 0
                vram_total = 0

            try:
                usage = n.nvmlDeviceGetUtilizationRates(h)
                gpu_usage = usage.gpu
            except Exception:
                gpu_usage = 0

            try:
                temp = n.nvmlDeviceGetTemperature(
                    h,
                    n.NVML_TEMPERATURE_GPU
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
                power_limit = (
                    n.nvmlDeviceGetPowerManagementLimit(h) / 1000.0
                )
            except Exception:
                power_limit = 0.0

            try:
                clock = n.nvmlDeviceGetClockInfo(
                    h,
                    n.NVML_CLOCK_GRAPHICS
                )
            except Exception:
                clock = 0

            try:
                memclock = n.nvmlDeviceGetClockInfo(
                    h,
                    n.NVML_CLOCK_MEM
                )
            except Exception:
                memclock = 0

            try:
                fan = n.nvmlDeviceGetFanSpeed(h)
                fan_available = True
            except Exception:
                fan = 0
                fan_available = False

            result.append({
                "name": name,
                "gpu": gpu_usage,
                "vram_used": vram_used,
                "vram_total": vram_total,
                "temp": temp,
                "power": power,
                "power_available": power_available,
                "power_limit": power_limit,
                "clock": clock,
                "memclock": memclock,
                "fan": fan,
                "fan_available": fan_available
            })

        return result

    except Exception:
        return []

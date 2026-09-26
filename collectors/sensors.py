import psutil

def get_sensors():
    out={"temperatures":{},"fans":{},"battery":None}
    try:
        for name,items in psutil.sensors_temperatures().items():
            out["temperatures"][name]=[{"label":x.label,"current":x.current,"high":x.high,"critical":x.critical} for x in items]
    except Exception: pass
    try:
        for name,items in psutil.sensors_fans().items():
            out["fans"][name]=[{"label":x.label,"current":x.current} for x in items]
    except Exception: pass
    try:
        b=psutil.sensors_battery()
        if b: out["battery"]={"percent":b.percent,"plugged":b.power_plugged,"secsleft":b.secsleft}
    except Exception: pass
    return out

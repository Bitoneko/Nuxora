import psutil

def get_battery():
    try:
        b=psutil.sensors_battery()
        if not b:return None
        return {"percent":b.percent,"plugged":b.power_plugged,"seconds_left":b.secsleft}
    except Exception:return None

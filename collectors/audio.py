import subprocess

def get_audio():
    try:
        r=subprocess.run(["wpctl","status"],capture_output=True,text=True,timeout=3)
        return r.stdout.splitlines()
    except Exception:
        try:
            r=subprocess.run(["pactl","list","short","sinks"],capture_output=True,text=True,timeout=3)
            return r.stdout.splitlines()
        except Exception:return []
          

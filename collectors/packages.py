import subprocess

def get_packages():
    managers=[
        ("apt",["dpkg-query","-W","-f=${Package}\t${Version}\n"]),
        ("rpm",["rpm","-qa","--qf","%{NAME}\t%{VERSION}-%{RELEASE}\n"]),
        ("pacman",["pacman","-Q"])
    ]
    for name,cmd in managers:
        try:
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=8)
            if r.returncode==0:
                return {"manager":name,"packages":r.stdout.splitlines()}
        except Exception:pass
    return {"manager":None,"packages":[]}

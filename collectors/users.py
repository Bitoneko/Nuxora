import psutil

def get_users():
    out=[]
    for u in psutil.users():
        out.append({
            "name":u.name,"terminal":u.terminal,
            "host":u.host,"started":u.started,"pid":u.pid
        })
    return out

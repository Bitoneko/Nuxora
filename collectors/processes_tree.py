import psutil

def get_process_tree():
    procs={}
    for p in psutil.process_iter(["pid","ppid","name"]):
        try:
            i=p.info
            procs[i["pid"]]={"pid":i["pid"],"ppid":i["ppid"],"name":i["name"] or "?"}
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    tree={}
    for p in procs.values():tree.setdefault(p["ppid"],[]).append(p)
    return tree

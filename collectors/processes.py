import psutil

def get_processes():
    result=[]
    for p in psutil.process_iter([
        "pid","name","cpu_percent","memory_percent","memory_info","status"
    ]):
        try:
            i=p.info;m=i["memory_info"]
            result.append({
                "pid":i["pid"],
                "name":i["name"] or "?",
                "cpu":i["cpu_percent"] or 0,
                "ram":i["memory_percent"] or 0,
                "memory":m.rss if m else 0,
                "status":i["status"] or "?"
            })
        except (psutil.NoSuchProcess,psutil.AccessDenied):
            pass
    return sorted(result,key=lambda x:x["cpu"],reverse=True)

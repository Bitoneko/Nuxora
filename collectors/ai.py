import psutil

def get_ai_processes():
    keys=("python","python3","torch","ollama","stable","comfy","forge","cuda")
    out=[]
    for p in psutil.process_iter(["pid","name","cmdline","cpu_percent","memory_info"]):
        try:
            i=p.info
            text=" ".join(i["cmdline"] or []).lower()
            name=(i["name"] or "").lower()
            if any(k in name or k in text for k in keys):
                out.append({
                    "pid":i["pid"],"name":i["name"] or "?",
                    "cpu":i["cpu_percent"] or 0,
                    "memory":i["memory_info"].rss if i["memory_info"] else 0,
                    "cmdline":text
                })
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return out

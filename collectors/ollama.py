import json,urllib.request

def get_ollama():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/ps",timeout=2) as r:
            return json.load(r).get("models",[])
    except Exception:return []

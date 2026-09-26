import psutil

def get_memory():
    return {
        "ram": psutil.virtual_memory(),
        "swap": psutil.swap_memory()
    }

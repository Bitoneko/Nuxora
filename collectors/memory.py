import psutil

def get_memory():
    return psutil.virtual_memory(),psutil.swap_memory()

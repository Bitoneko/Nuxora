import psutil

def get_network():
    return {
        "total":psutil.net_io_counters(),
        "interfaces":psutil.net_io_counters(pernic=True),
        "connections":psutil.net_connections(kind="inet")
    }

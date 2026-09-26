import psutil,os

def get_filesystems():
    out=[]
    for p in psutil.disk_partitions(all=True):
        try:
            u=psutil.disk_usage(p.mountpoint)
            st=os.statvfs(p.mountpoint)
            out.append({
                "device":p.device,"mount":p.mountpoint,"fstype":p.fstype,
                "total":u.total,"used":u.used,"free":u.free,"percent":u.percent,
                "inodes_total":st.f_files,"inodes_free":st.f_ffree,
                "inodes_percent":(1-st.f_ffree/st.f_files)*100 if st.f_files else 0
            })
        except Exception:pass
    return out

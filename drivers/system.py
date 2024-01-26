import psutil, socket
from nettemp import insert2

def system():
    print("[ nettemp client ][ system ] start")

    group = socket.gethostname()
    data = []

    cpu=psutil.cpu_percent()
    mem=psutil.virtual_memory().percent

    rom=group+'_system_cpu'
    type='system'
    value=cpu
    name='CPU'
    data.append({"rom":rom,"type":type, "value":value,"name":name, "group":group})

    rom=group+'_system_mem'
    type='system'
    value=mem
    name='Memory'
    data.append({"rom":rom,"type":type, "value":value,"name":name, "group":group})

    data=insert2(data)
    data.request()
    #print(f"[ nettemp client ] {data}")
    print("[ nettemp client ][ system ] End")
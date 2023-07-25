import psutil, socket
from nettemp import insert

def system():
    group = socket.gethostname()

    cpu=psutil.cpu_percent()
    mem=psutil.virtual_memory().percent

    rom=group+'_system_cpu'
    type='system'
    value=cpu
    name='CPU'
    data=insert(rom, type, value, name, group)
    data.request()

    rom=group+'_system_mem'
    type='system'
    value=mem
    name='Memory'
    data=insert(rom, type, value, name, group)
    data.request()
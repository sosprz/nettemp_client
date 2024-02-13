import psutil, socket
from nettemp import insert2
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def system():
    logging.info("[ nettemp client ][ system ] start")

    
    data = []

    cpu=psutil.cpu_percent()
    mem=psutil.virtual_memory().percent

    rom='_system_cpu'
    type='system'
    value=cpu
    name='CPU'
    data.append({"rom":rom,"type":type, "value":value,"name":name})

    rom='_system_mem'
    type='system'
    value=mem
    name='Memory'
    data.append({"rom":rom,"type":type, "value":value,"name":name})

    data=insert2(data)
    data.request()

    logging.info("[  nettemp client  ][ system ] End")
import psutil, socket
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def system(config_dict):
	data = []

	cpu = psutil.cpu_percent()
	mem = psutil.virtual_memory().percent

	rom = '_system_cpu'
	type = 'system'
	value = cpu
	name = 'CPU'
	data.append({"rom":rom,"type":type, "value":value,"name":name})

	rom = '_system_mem'
	type = 'system'
	value = mem
	name = 'Memory'
	data.append({"rom":rom,"type":type, "value":value,"name":name})

	return data

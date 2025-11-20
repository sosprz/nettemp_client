import io, sys, os, socket



def rpi(config_dict):
	try:
		print("Rpi")
		from gpiozero import CPUTemperature
		cpu = CPUTemperature()
		data = []

		value = cpu.temperature
		rom = '_raspberrypi'
		type = 'temp'
		name = 'raspberrypi'

		data.append({"rom":rom,"type":type, "value":value,"name":name})
		return data
	except Exception as e:
		print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
		print("No Rpi")
		return []




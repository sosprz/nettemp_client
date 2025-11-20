import smbus, time, sys, os, socket

def tmp102(config_dict):
	if len(sys.argv) > 1:
		nbus = sys.argv[1]
	elif  os.path.exists("/dev/i2c-0"):
		nbus = "0"
	elif os.path.exists("/dev/i2c-1"):
		nbus = "1"
	elif os.path.exists("/dev/i2c-2"):
		nbus = "2"
	elif os.path.exists("/dev/i2c-3"):
		nbus = "3"
	else:
		nbus = "1"

	try:
		bus = smbus.SMBus(int(nbus))
		data = bus.read_i2c_block_data(0x48, 0)
		msb = data[0]
		lsb = data[1]
		rom = "_i2c_48_temp"
		value = '{0:0.2f}'.format((((msb << 8) | lsb) >> 4) * 0.0625)
		name = 'tmp102'
		type = 'temp'
		return [{"rom":rom,"type":type, "value":value,"name":name}]
	except Exception:
		print("No TMP102")
		return []

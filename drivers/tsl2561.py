import time, socket
import board
import busio
import adafruit_tsl2561

def tsl2561(config_dict):
	try:
		i2c = busio.I2C(board.SCL, board.SDA)
		tsl = adafruit_tsl2561.TSL2561(i2c)

		# Enable the light sensor
		tsl.enabled = True
		time.sleep(1)

		# Set gain 0=1x, 1=16x
		tsl.gain = 0

		# Set integration time (0=13.7ms, 1=101ms, 2=402ms, or 3=manual)
		tsl.integration_time = 1

		# Get computed lux value (tsl.lux can return None or a float)
		lux = tsl.lux

		rom = "_i2c_39_lux"
		if lux:
			value = '{0:0.2f}'.format(lux)
		else:
			value = 0
		name = 'tsl2561_lux'
		type = 'lux'
		return [{"rom":rom,"type":type, "value":value,"name":name}]
	except Exception:
		print("No TSL2561")
		return []
	finally:
		try:
			tsl.enabled = False
		except Exception:
			pass

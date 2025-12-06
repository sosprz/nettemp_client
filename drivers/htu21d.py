import time
import board
import busio
from adafruit_htu21d import HTU21D
import sys, os, socket

def htu21d(config_dict):
  try:
    # Create library object using our Bus I2C port
    i2c = busio.I2C(board.SCL, board.SDA)
    
    data = []

    sensor = HTU21D(i2c)
    
    # Get I2C address from config (for rom naming), default 0x40
    addr_str = config_dict.get("i2c_address", "0x40")
    if isinstance(addr_str, str) and addr_str.startswith('0x'):
        addr_hex = addr_str[2:]
    else:
        addr_hex = "40"
    
    rom = f"_i2c_{addr_hex}_temp"
    value = '{0:0.2f}'.format(sensor.temperature)
    name = 'htu21d_temp'
    type = 'temp'
    data.append({"rom":rom,"type":type, "value":value,"name":name})

    rom = f"_i2c_{addr_hex}_humid"
    value = '{0:0.2f}'.format(sensor.relative_humidity)
    name = 'htu21d_humid'
    type = 'humid'
    data.append({"rom":rom,"type":type, "value":value,"name":name})

    return data
  except Exception as e:
    # Suppress full traceback for common "device not found" errors
    if "No I2C device" in str(e) or "Remote I/O error" in str(e):
        print("HTU21D: Sensor not found at configured address")
    else:
        print(f"HTU21D Error: {e}")
        import traceback
        traceback.print_exc()
    return []
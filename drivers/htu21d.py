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
    rom = "_i2c_40_temp"
    value = '{0:0.2f}'.format(sensor.temperature)
    name = 'htu21d_temp'
    type = 'temp'
    data.append({"rom":rom,"type":type, "value":value,"name":name})

    rom = "_i2c_40_humid"
    value = '{0:0.2f}'.format(sensor.relative_humidity)
    name = 'htu21d_humid'
    type = 'humid'
    data.append({"rom":rom,"type":type, "value":value,"name":name})

    return data
  except:
    print ("No HTU21d")
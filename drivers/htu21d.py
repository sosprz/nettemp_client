import time
import board
import busio
from adafruit_htu21d import HTU21D
import sys, os, socket
from nettemp import insert

def htu21d():
  try:
    # Create library object using our Bus I2C port
    i2c = busio.I2C(board.SCL, board.SDA)
    group = socket.gethostname()
    sensor = HTU21D(i2c)
    rom = group+"_i2c_40_temp"
    value = '{0:0.2f}'.format(sensor.temperature)
    name = 'htu21d_temp'
    type = 'temp'
    data=insert(rom, type, value, name, group)
    data.request()

    rom = group+"_i2c_40_humid"
    value = '{0:0.2f}'.format(sensor.relative_humidity)
    name = 'htu21d_humid'
    type = 'humid'
    data=insert(rom, type, value, name, group)
    data.request()
  except:
    print ("No HTU21d")
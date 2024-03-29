import time
import board
import busio
import adafruit_adxl34x
import sys
import os.path, socket
from nettemp import insert
i2c = busio.I2C(board.SCL, board.SDA)

accelerometer = adafruit_adxl34x.ADXL343(i2c)
accelerometer.enable_motion_detection()

if accelerometer.events["motion"]==True:
    motion=1
else:
    motion=0

#print("Motion detected: %s" % accelerometer.events["motion"])
#print(accelerometer.acceleration)

try:
  data = accelerometer.acceleration
  x = '{0:0.2f}'.format(data[0])
  y = '{0:0.2f}'.format(data[1])
  z = '{0:0.2f}'.format(data[2])

  

  rom = "i2c_53_acce_x"
  value = x
  name = 'adxl343_x'
  type = 'accel'
  data=insert(rom, type, value, name)
  data.request()

  rom = "i2c_53_acce_y"
  value = y
  name = 'adxl343_y'
  type = 'accel'
  data=insert(rom, type, value, name)
  data.request()

  rom = "i2c_53_acce_z"
  value = z
  name = 'adxl343_z'
  type = 'accel'
  data=insert(rom, type, value, name)
  data.request()

  rom = "i2c_53_moti"
  value = '{0:0.2f}'.format(motion)
  name = 'adxl343_motion'
  type = 'motion'
  data=insert(rom, type, value, name)
  data.request()
except:
  print ("No ADXL34x")

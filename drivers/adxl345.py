import time
import board
import busio
import adafruit_adxl34x
import sys
import os.path, socket
from nettemp import insert, insert2
i2c = busio.I2C(board.SCL, board.SDA)

def adxl345():
  print ("ADXL34x")
  try:
      print ("ADXL34x")
      accelerometer = adafruit_adxl34x.ADXL345(i2c)
      accelerometer.enable_motion_detection()

      if accelerometer.events["motion"]==True:
          motion=1
      else:
          motion=0

      #print("Motion detected: %s" % accelerometer.events["motion"])
      #print(accelerometer.acceleration)
      
      data = accelerometer.acceleration
      x = '{0:0.2f}'.format(data[0])
      y = '{0:0.2f}'.format(data[1])
      z = '{0:0.2f}'.format(data[2])

      group = socket.gethostname()

      rom = group+"_i2c_53_acce_x"
      value = x
      name = 'adxl345_x'
      type = 'accel'
      data=insert2(rom, type, value, name, group)

      rom = group+"_i2c_53_acce_y"
      value = y
      name = 'adxl345_y'
      type = 'accel'
      data=insert2(rom, type, value, name, group)

      rom = group+"_i2c_53_acce_z"
      value = z
      name = 'adxl345_z'
      type = 'accel'
      data=insert2(rom, type, value, name, group)


      rom = group+"_i2c_53_moti"
      value = '{0:0.2f}'.format(motion)
      name = 'adxl345_motion'
      type = 'motion'
      data=insert2(rom, type, value, name, group)

      data.request()

  except:
      print ("No ADXL34x")


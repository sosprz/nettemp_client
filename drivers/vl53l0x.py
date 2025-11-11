import board
import busio
import adafruit_vl53l0x
import socket

def vl53l0x(config_dict):
  print ("vl53l0x")
  try:
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_vl53l0x.VL53L0X(i2c)
    
    #print('Range: {}mm'.format(sensor.range))
    rom = "_i2c_29_dist"
    value = '{0:0.2f}'.format(sensor.range/10) #cm
    name = 'vl53l0x_dist'
    type = 'dist'
    return [{"rom":rom,"type":type, "value":value,"name":name}]
  except:
    print ("No vl53l0x")




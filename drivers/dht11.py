import time, socket
import board
import adafruit_dht

from nettemp import insert2

def dht11(*args):
  print("DHT11")
  try:
    pin = str(args[0])
    pin = "D"+pin
    print(pin)
    dht_device = adafruit_dht.DHT11(getattr(board,pin))
    temperature = dht_device.temperature
    humidity = dht_device.humidity
    dht_device.exit()
    print(temperature)
    print(humidity)
    
    data = []

    if humidity is not None and temperature is not None:
      value = '{0:0.1f}'.format(temperature)
      rom = '_dht11_temp_gpio_'+pin
      type = 'temp'
      name = rom
      data.append({"rom":rom,"type":type, "value":value,"name":name})
    
      value = '{0:0.1f}'.format(humidity)
      rom = '_dht11_humid_gpio_'+pin
      type = 'humid'
      name = rom
      data.append({"rom":rom,"type":type, "value":value,"name":name})

      data=insert2(data)
      data.request()

  except:
    print("No DHT11")
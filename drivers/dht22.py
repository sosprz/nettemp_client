import time, socket
import board
import adafruit_dht

from nettemp import insert2

def dht22():
  print("DHT22")
  #try:
  pin = 4
  pin = "D"+pin
  dht_device = adafruit_dht.DHT22(getattr(board,pin))
  temperature = dht_device.temperature
  humidity = dht_device.humidity
  print(temperature)
  print(humidity)
  group = socket.gethostname()
  data = []

  if humidity is not None and temperature is not None:
    value = '{0:0.1f}'.format(temperature)
    rom = group+'_dht22_temp_gpio_'+pin
    type = 'temp'
    name = rom
    data.append({"rom":rom,"type":type, "value":value,"name":name, "group":group})
  
    value = '{0:0.1f}'.format(humidity)
    rom = group+'_dht22_humid_gpio_'+pin
    type = 'humid'
    name = rom
    data.append({"rom":rom,"type":type, "value":value,"name":name, "group":group})

    data=insert2(data)
    data.request()

  #except:
  #  print("No DHT22")
import time
import board
import adafruit_dht

from nettemp import insert2



pin

  pin = 'D'+pin
  dht_device = adafruit_dht.DHT22(getattr(board, pin))

  temperature = dht_device.temperature
  humidity = dht_device.humidity

  if humidity is not None and temperature is not None:
    value = '{0:0.1f}'.format(temperature)
    rom = 'dht22_temp_gpio_'+i
    type = 'temp'
    name = rom

   
    value = '{0:0.1f}'.format(humidity)
    rom = 'dht22_humid_gpio_'+i
    type = 'humid'
    name = rom
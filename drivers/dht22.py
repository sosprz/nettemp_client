import time, socket
import board
import adafruit_dht


def dht22(config_dict):
  print("DHT22")
  try:
    pin = str(config_dict.get("gpio_pin"))
    pin = "D"+pin
    print(pin)
    dht_device = adafruit_dht.DHT22(getattr(board,pin))
    temperature = dht_device.temperature
    humidity = dht_device.humidity
    dht_device.exit()
    print(temperature)
    print(humidity)
    
    data = []

    if humidity is not None and temperature is not None:
      value = '{0:0.1f}'.format(temperature)
      rom = '_dht22_temp_gpio_'+pin
      type = 'temp'
      name = rom
      data.append({"rom":rom,"type":type, "value":value,"name":name})
    
      value = '{0:0.1f}'.format(humidity)
      rom = '_dht22_humid_gpio_'+pin
      type = 'humid'
      name = rom
      data.append({"rom":rom,"type":type, "value":value,"name":name})

    return data

  except:
    print("No DHT22")
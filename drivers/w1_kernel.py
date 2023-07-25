import requests, socket
import sys, os, random, json
from nettemp import insert

def w1_kernel():
    try:
        from w1thermsensor import W1ThermSensor
        group = socket.gethostname()
        for sensor in W1ThermSensor.get_available_sensors():
            r = random.randint(10000,99999)
            value = sensor.get_temperature()
            rom = group+'_28_'+sensor.id
            type = 'temp'
            name = 'DS18b20-'+str(r)
            data=insert(rom, type, value, name, group)
            data.request()
    except:
        print ("No w1_kernel")

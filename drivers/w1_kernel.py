import socket, random
from nettemp import insert2

def w1_kernel():

    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    print ("w1_kernel")
    try:
        from w1thermsensor import W1ThermSensor
        group = socket.gethostname()
        data = []

        for sensor in W1ThermSensor.get_available_sensors():
            r = random.randint(10000,99999)
            value = sensor.get_temperature()
            rom = group+'_28_'+sensor.id
            type = 'temp'
            name = 'DS18b20-'+str(r)
            data.append({"rom":rom,"type":type, "value":value,"name":name, "group":group})

        data=insert2(data)
        data.request()

    except:
        print ("No w1_kernel")

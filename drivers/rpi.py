import io, sys, os, socket
from nettemp import insert2



def rpi():
    try:
        print("Rpi")
        from gpiozero import CPUTemperature
        cpu = CPUTemperature()
        data = []
        
        value = cpu.temperature
        rom = '_raspberrypi'
        type = 'temp'
        name = 'raspberrypi'

        data.append({"rom":rom,"type":type, "value":value,"name":name})
        data=insert2(data)
        data.request()
    except Exception as e:
        print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
        print("No Rpi")





import io, sys, os, socket
from nettemp import insert



def rpi():
    try:
        print("Rpi")
        from gpiozero import CPUTemperature
        cpu = CPUTemperature()
        
        value = cpu.temperature
        rom = '_raspberrypi'
        type = 'temp'
        name = '_raspberrypi'
        data=insert(rom, type, value, name)
        data.request()
    except Exception as e:
        print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
        print("No Rpi")





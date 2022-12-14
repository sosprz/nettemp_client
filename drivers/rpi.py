import io, sys, os, socket
from nettemp import insert



def rpi():
    try:
        from gpiozero import CPUTemperature
        cpu = CPUTemperature()
        group = socket.gethostname()
        value = cpu.temperature
        rom = group+'_raspberrypi'
        type = 'temp'
        name = group+'_raspberrypi'
        data=insert(rom, type, value, name, group)
        data.request()
    except Exception as e:
        print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
        print("No Rpi")





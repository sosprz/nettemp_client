import smbus, time, sys, os, socket
from nettemp import insert

def tmp102():
    print("TMP102")
    if len(sys.argv) > 1:
        nbus = sys.argv[1]
    elif  os.path.exists("/dev/i2c-0"):
        nbus = "0"
    elif os.path.exists("/dev/i2c-1"):
        nbus = "1"
    elif os.path.exists("/dev/i2c-2"):
        nbus = "2"
    elif os.path.exists("/dev/i2c-3"):
        nbus = "3"

    try:
        
        bus = smbus.SMBus(int(nbus))
        data = bus.read_i2c_block_data(0x48, 0)
        msb = data[0]
        lsb = data[1]
        # Print degrees Celsius
        rom = "_i2c_48_temp"
        value = '{0:0.2f}'.format((((msb << 8) | lsb) >> 4) * 0.0625)
        name = 'tmp102'
        type = 'temp'
        data=insert(rom, type, value, name)
        data.request()
    except: 
        print("No TMP102")
        

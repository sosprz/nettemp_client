#!/usr/bin/python
# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Can enable debug output by uncommenting:
#import logging
#logging.basicConfig(level=logging.DEBUG)

import Adafruit_BMP.BMP085 as BMP085
import socket, sys, os
from nettemp import insert2

# Default constructor will pick a default I2C bus.
#
# For the Raspberry Pi this means you should hook up to the only exposed I2C bus
# from the main GPIO header and the library will figure out the bus number based
# on the Pi's revision.
#
# For the Beaglebone Black the library will assume bus 1 by default, which is
# exposed with SCL = P9_19 and SDA = P9_20.
def bmp180():
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

    #sensor = BMP085.BMP085(busnum=int(nbus))

    # Optionally you can override the nbus number:
    #sensor = BMP085.BMP085(nbusnum=2)

    # You can also optionally change the BMP085 mode to one of BMP085_ULTRALOWPOWER, 
    # BMP085_STANDARD, BMP085_HIGHRES, or BMP085_ULTRAHIGHRES.  See the BMP085
    # datasheet for more details on the meanings of each mode (accuracy and power
    # consumption are primarily the differences).  The default mode is STANDARD.
    #sensor = BMP085.BMP085(mode=BMP085.BMP085_ULTRAHIGHRES)

    #print(sensor.read_temperature())
    #print(sensor.read_pressure()*0.01)
    #print '{0:0.2f}'.format(sensor.read_altitude())
    #print '{0:0.2f}'.format(sensor.read_sealevel_pressure())

    try:
        print("BMP180")
        sensor = BMP085.BMP085(busnum=int(nbus))
        
        data = []

        rom = "_i2c_77_temp"
        value = '{0:0.2f}'.format(sensor.read_temperature())
        name = 'bmp180_temp'
        type = 'temp'
        data.append({"rom":rom,"type":type, "value":value,"name":name})

        rom = "_i2c_77_press"
        value = '{0:0.2f}'.format(sensor.read_pressure()*0.01)
        name = 'bmp180_press'
        type = 'press'
        data.append({"rom":rom,"type":type, "value":value,"name":name})

        data=insert2(data)
        data.request()
    except:
        print("No BMP180")



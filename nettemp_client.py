
from time import sleep
import yaml, os, time, smbus
os.chdir(os.path.dirname(__file__))
from apscheduler.schedulers.background import BackgroundScheduler
sched = BackgroundScheduler({'apscheduler.timezone': 'Europe/London'})

sched.start()

config_file = open("config.conf")
config = yaml.load(config_file, Loader=yaml.FullLoader)

w1_kernel_enabled = config["w1_kernel"]["enabled"]
w1_kernel_read_in_sec = config["w1_kernel"]["read_in_sec"]

rpi_enabled = config["rpi"]["enabled"]
rpi_read_in_sec = config["rpi"]["read_in_sec"]

bmp180_enabled = config["bmp180"]["enabled"]
bmp180_read_in_sec = config["bmp180"]["read_in_sec"]

bme280_enabled = config["bme280"]["enabled"]
bme280_read_in_sec = config["bme280"]["read_in_sec"]

htu21d_enabled = config["htu21d"]["enabled"]
htu21d_read_in_sec = config["htu21d"]["read_in_sec"]


if config["bh1750"]["enabled"] and config["bh1750"]["read_in_sec"]:
  from drivers.bh1750 import bh1750 
  try:
    bh1750()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(bh1750, 'interval', seconds = config["bh1750"]["read_in_sec"])

if config["system"]["enabled"] and config["system"]["read_in_sec"]:
  from drivers.system import system 
  try:
    system()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(system, 'interval', seconds = config["system"]["read_in_sec"])

if config["tmp102"]["enabled"] and config["tmp102"]["read_in_sec"]:
  from drivers.tmp102 import tmp102 
  try:
    tmp102()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(tmp102, 'interval', seconds = config["tmp102"]["read_in_sec"])

if rpi_enabled and rpi_read_in_sec:
  from drivers.rpi import rpi 
  try:
    rpi()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(rpi, 'interval', seconds = rpi_read_in_sec)

if bmp180_enabled and bmp180_read_in_sec:
  from drivers.bmp180 import bmp180 
  try:
    bmp180()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(bmp180, 'interval', seconds = bmp180_read_in_sec)

if bme280_enabled and bme280_read_in_sec:
  from drivers.bme280 import bme280 
  try:
    bme280()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(bme280, 'interval', seconds = bme280_read_in_sec)

if htu21d_enabled and htu21d_read_in_sec:
  from drivers.htu21d import htu21d 
  try:
    htu21d()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(htu21d, 'interval', seconds = htu21d_read_in_sec)

if w1_kernel_enabled and w1_kernel_read_in_sec:
  from drivers.w1_kernel import w1_kernel
  try:
    os.system('sudo bash drivers/ds2482.sh')
    w1_kernel()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(w1_kernel, 'interval', seconds = w1_kernel_read_in_sec)


while True:
    sleep(1)



    



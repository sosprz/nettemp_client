
from time import sleep
import yaml, os, time, smbus
os.chdir(os.path.dirname(__file__))
from apscheduler.schedulers.background import BackgroundScheduler
sched = BackgroundScheduler({'apscheduler.timezone': 'Europe/London'})

sched.start()

config_file = open("config.conf")
config = yaml.load(config_file, Loader=yaml.FullLoader)

if config["dht22"]["enabled"] and config["dht22"]["read_in_sec"] and config["dht22"]["gpio_pin"]:
  from drivers.dht22 import dht22
  try:
    dht22(config["dht22"]["gpio_pin"])
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(dht22, 'interval', seconds = config["dht22"]["read_in_sec"], args=[config["dht22"]["gpio_pin"]])

if config["dht11"]["enabled"] and config["dht11"]["read_in_sec"] and config["dht11"]["gpio_pin"]:
  from drivers.dht11 import dht11
  try:
    dht11(config["dht11"]["gpio_pin"])
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(dht11, 'interval', seconds = config["dht11"]["read_in_sec"], args=[config["dht11"]["gpio_pin"]])

if config["mpl3115a2"]["enabled"] and config["mpl3115a2"]["read_in_sec"]:
  from drivers.mpl3115a2 import mpl3115a2
  try:
    mpl3115a2()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(mpl3115a2, 'interval', seconds = config["mpl3115a2"]["read_in_sec"])

if config["tsl2561"]["enabled"] and config["tsl2561"]["read_in_sec"]:
  from drivers.tsl2561 import tsl2561 
  try:
    tsl2561()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(tsl2561, 'interval', seconds = config["tsl2561"]["read_in_sec"])

if config["hih6130"]["enabled"] and config["hih6130"]["read_in_sec"]:
  from drivers.hih6130 import hih6130 
  try:
    hih6130()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(hih6130, 'interval', seconds = config["hih6130"]["read_in_sec"])

if config["bh1750"]["enabled"] and config["bh1750"]["read_in_sec"]:
  from drivers.bh1750 import bh1750 
  try:
    bh1750()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(bh1750, 'interval', seconds = config["bh1750"]["read_in_sec"])

if config["adxl345"]["enabled"] and config["adxl345"]["read_in_sec"]:
  from drivers.adxl345 import adxl345
  try:
    adxl345()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(adxl345, 'interval', seconds = config["adxl345"]["read_in_sec"])

if config["vl53l0x"]["enabled"] and config["vl53l0x"]["read_in_sec"]:
  from drivers.vl53l0x import vl53l0x
  try:
    vl53l0x()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(vl53l0x, 'interval', seconds = config["vl53l0x"]["read_in_sec"])

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

if config["rpi"]["enabled"] and config["rpi"]["read_in_sec"]:
  from drivers.rpi import rpi 
  try:
    rpi()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(rpi, 'interval', seconds = config["rpi"]["read_in_sec"])

if config["bmp180"]["enabled"] and config["bmp180"]["read_in_sec"]:
  from drivers.bmp180 import bmp180 
  try:
    bmp180()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(bmp180, 'interval', seconds = config["bmp180"]["read_in_sec"])

if config["bme280"]["enabled"] and config["bme280"]["read_in_sec"]:
  from drivers.bme280 import bme280 
  try:
    bme280()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(bme280, 'interval', seconds = config["bme280"]["read_in_sec"])

if config["htu21d"]["enabled"] and config["htu21d"]["read_in_sec"]:
  from drivers.htu21d import htu21d 
  try:
    htu21d()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(htu21d, 'interval', seconds = config["htu21d"]["read_in_sec"])

if config["w1_kernel_gpio"]["enabled"] and config["w1_kernel_gpio"]["read_in_sec"]:
  from drivers.w1_kernel_gpio import w1_kernel_gpio
  try:
    w1_kernel_gpio()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(w1_kernel_gpio, 'interval', seconds = config["w1_kernel_gpio"]["read_in_sec"])

if config["w1_kernel"]["enabled"] and config["w1_kernel"]["read_in_sec"]:
  from drivers.w1_kernel import w1_kernel
  try:
    os.system('sudo bash drivers/ds2482.sh')
    w1_kernel()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(w1_kernel, 'interval', seconds = config["w1_kernel"]["read_in_sec"])

while True:
    sleep(1)



    




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

system_enabled = config["system"]["enabled"]
system_read_in_sec = config["system"]["read_in_sec"]

tmp102_enabled = config["tmp102"]["enabled"]
tmp102_read_in_sec = config["tmp102"]["read_in_sec"]

rpi_enabled = config["rpi"]["enabled"]
rpi_read_in_sec = config["rpi"]["read_in_sec"]

if system_enabled and system_read_in_sec:
  from drivers.system import system 
  try:
    system()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(system, 'interval', seconds = system_read_in_sec)

if w1_kernel_enabled and w1_kernel_read_in_sec:
  from drivers.w1_kernel import w1_kernel
  try:
    os.system('sudo bash drivers/ds2482.sh')
    w1_kernel()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(w1_kernel, 'interval', seconds = w1_kernel_read_in_sec)

if tmp102_enabled and tmp102_read_in_sec:
  from drivers.tmp102 import tmp102 
  try:
    tmp102()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(tmp102, 'interval', seconds = tmp102_read_in_sec)

if rpi_enabled and rpi_read_in_sec:
  from drivers.rpi import rpi 
  try:
    rpi()
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
  sched.add_job(rpi, 'interval', seconds = rpi_read_in_sec)



while True:
    sleep(1)



    



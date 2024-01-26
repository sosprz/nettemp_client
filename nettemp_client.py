
#!/usr/bin/env python

from time import sleep
import yaml, os, time, smbus, sys, hashlib
from nettemp import download_remote_config
os.chdir(os.path.dirname(__file__))
from apscheduler.schedulers.background import BackgroundScheduler
sched = BackgroundScheduler({'apscheduler.timezone': 'Europe/London'})

configm = "config.conf"
config_remote = "remote.conf"
configd = "drivers.conf"

def remote_config():
  config = yaml.load(open(configm), Loader=yaml.FullLoader)
  if config["remote_config"]['enabled']:
    return True
  else:
    return False

def load_md5_hash(file_path):
    with open(file_path, 'rb') as file_obj:
        return hashlib.md5(file_obj.read()).hexdigest()
      
def load_config(file_path):
    return yaml.safe_load(open(file_path, 'r'))

sched.start()

if remote_config():
    print("[ nettemp client ][ remote config: Enabled ]")
    if os.path.isfile(config_remote):
        config = load_config(config_remote)
        print("[ nettemp client ][ remote config exist ]")
    else:
        config = load_config(configd)
        print("[ nettemp client ][ no remote config using local  ]")
else:
    print("[ nettemp client ][ remote config: Disabled ]")
    config = load_config(configd)
    print("[ nettemp client ][ no remote config using local ]")
  
# drivers
 
def setup_sensor_driver(driver_name, driver_module, extra_args=None):
    driver_config = config.get(driver_name, {})

    if not (driver_config.get("enabled") and driver_config.get("read_in_sec")):
        return

    # Handle additional arguments like GPIO pins
    args = [driver_config.get("gpio_pin")] if extra_args else []

    try:
        getattr(driver_module, driver_name)(*args)
    except Exception as e:
        print(f"\n[WARN] {driver_name} Error \n\tArgs: '{str(e.args)}'")
    else:
        sched.add_job(
            getattr(driver_module, driver_name), 
            'interval', 
            seconds=driver_config["read_in_sec"],
            args=args
        )

# Usage
from drivers import dht22, dht11, mpl3115a2, tsl2561, hih6130, bh1750, adxl345, vl53l0x, system, tmp102, rpi, bmp180, bme280, htu21d, w1_kernel, w1_kernel_gpio, lm_sensors, ping

sensor_drivers = {
    "dht22": (dht22, True),
    "dht11": (dht11, True),
    "mpl3115a2": mpl3115a2,
    "tsl2561": tsl2561,
    "hih6130": hih6130,
    "bh1750": bh1750,
    "adxl345": adxl345,
    "vl53l0x": vl53l0x,
    "system": system,
    "tmp102": tmp102,
    "rpi": rpi,
    "bmp180": bmp180,
    "bme280": bme280,
    "htu21d": htu21d,
    "w1_kernel": w1_kernel,
    "w1_kernel_gpio": w1_kernel_gpio,
    "lm_sensors": lm_sensors,
    "ping": ping,
}

# exception for ds2482
if config["w1_kernel"]["enabled"] and config["w1_kernel"]["read_in_sec"]:
  try:
    os.system('sudo bash drivers/ds2482.sh')
  except Exception as e:
    pass
    print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))

# rest 

for driver_name, driver_info in sensor_drivers.items():
    if isinstance(driver_info, tuple):
        setup_sensor_driver(driver_name, driver_info[0], extra_args=driver_info[1])
    else:
        setup_sensor_driver(driver_name, driver_info)


with open(configd, 'rb') as file_obj:
  configd_md5_hash = hashlib.md5(file_obj.read()).hexdigest()

with open(configm, 'rb') as file_obj:
  config_md5_hash = hashlib.md5(file_obj.read()).hexdigest()

while True:
  try:
    if remote_config() and download_remote_config():
      print("[ nettemp client ][ new remote config, restarting ]")
      os.execv(sys.executable, [sys.executable] + sys.argv)
  except:
    print("[ nettemp client ][ new remote config, problem ]")
  
  
  new_configd_md5_hash = load_md5_hash(configd)

  if configd_md5_hash != new_configd_md5_hash:
      print("[ nettemp client ][ new local driver config, restarting ]")
      os.execv(sys.executable, [sys.executable] + sys.argv)

  new_config_md5_hash = load_md5_hash(configm)

  if config_md5_hash != new_config_md5_hash:
      print("[ nettemp client ][ new local config, restarting ]")
      os.execv(sys.executable, [sys.executable] + sys.argv)
    
  sleep(60)




    



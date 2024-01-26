
#!/usr/bin/env python

from time import sleep
import yaml, os, time, smbus, sys, hashlib
from nettemp import download_remote_config
os.chdir(os.path.dirname(__file__))
from apscheduler.schedulers.background import BackgroundScheduler
sched = BackgroundScheduler({'apscheduler.timezone': 'Europe/London'})


# Load initial configurations

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

with open(configd, 'rb') as file_obj:
  configd_md5_hash = hashlib.md5(file_obj.read()).hexdigest()

with open(configm, 'rb') as file_obj:
  config_md5_hash = hashlib.md5(file_obj.read()).hexdigest()

# drivers

# exception for ds2482
try:
  if config["w1_kernel"]["enabled"] and config["w1_kernel"]["read_in_sec"]:
    try:
      os.system('sudo bash drivers/ds2482.sh')
    except Exception as e:
      pass
      print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
except Exception as e:
  pass
  print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))

# List of sensor configurations
sensor_configs = [
    {"name": "ping", "module": "drivers.ping", "extra_args": []},
    {"name": "dht22", "module": "drivers.dht22", "extra_args": ["gpio_pin"]},
    {"name": "dht11", "module": "drivers.dht11", "extra_args": ["gpio_pin"]},
    {"name": "mpl3115a2", "module": "drivers.mpl3115a2", "extra_args": []},
    {"name": "tsl2561", "module": "drivers.tsl2561", "extra_args": []},
    {"name": "hih6130", "module": "drivers.hih6130", "extra_args": []},
    {"name": "bh1750", "module": "drivers.bh1750", "extra_args": []},
    {"name": "adxl345", "module": "drivers.adxl345", "extra_args": []},
    {"name": "vl53l0x", "module": "drivers.vl53l0x", "extra_args": []},
    {"name": "system", "module": "drivers.system", "extra_args": []},
    {"name": "tmp102", "module": "drivers.tmp102", "extra_args": []},
    {"name": "rpi", "module": "drivers.rpi", "extra_args": []},
    {"name": "bmp180", "module": "drivers.bmp180", "extra_args": []},
    {"name": "bme280", "module": "drivers.bme280", "extra_args": []},
    {"name": "htu21d", "module": "drivers.htu21d", "extra_args": []},
    {"name": "w1_kernel_gpio", "module": "drivers.w1_kernel_gpio", "extra_args": []},
    {"name": "lm_sensors", "module": "drivers.lm_sensors", "extra_args": []},
    {"name": "w1_kernel", "module": "drivers.w1_kernel", "extra_args": []},
]

# Iterate over sensor configurations
for sensor_config in sensor_configs:
    sensor_name = sensor_config["name"]
    sensor_module = sensor_config["module"]
    extra_args = sensor_config.get("extra_args", [])

    # Check if the sensor_name key exists in the config dictionary
    if sensor_name in config and config[sensor_name]["enabled"] and config[sensor_name]["read_in_sec"]:
        try:
            module = __import__(sensor_module, fromlist=[sensor_name])
            getattr(module, sensor_name)(*extra_args)
        except Exception as e:
            pass
            print(f"\n[WARN] {sensor_name} Error \n\tArgs: '{str(e.args)}'")
        else:
            sched.add_job(
                getattr(module, sensor_name),
                'interval',
                seconds=config[sensor_name]["read_in_sec"],
                args=extra_args
            )
            

# Main loop for config checking and restart

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




    



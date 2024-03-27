#!/usr/bin/env python

import os
import sys
import time
import yaml
import hashlib
import logging
import requests
import argparse
import socket
from datetime import datetime
requests.packages.urllib3.disable_warnings() 
from apscheduler.schedulers.background import BackgroundScheduler
from requests.exceptions import RequestException

# Setup argument parser
parser = argparse.ArgumentParser(description='nettemp_client')
parser.add_argument('--debug', help='Enable debug logging', action='store_true')

# Parse arguments
args = parser.parse_args()

# Determine the logging level
if args.debug:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO

# Setup logging
logging.basicConfig(level=log_level, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Constants
CONFIG_MAIN = "config.conf"
CONFIG_REMOTE = "remote.conf"
# CONFIG_LOCAL = "local.conf"
CONFIG_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
logging.info(CONFIG_DIRECTORY)

# check config params




# Scheduler setup
sched = BackgroundScheduler({'apscheduler.timezone': 'Europe/Warsaw'})
sched.start()

# Helper functions

def check_config(config_path):

    # Define the expected parameters and their default values to check against
    expected_parameters = {
        'server': 'https://default_server',
        'server_api_key': 'default_key'
    }
    
    # Define all expected parameter names (including nested ones)
    all_expected_names = [
        'group',
        # 'remote_config.enabled',
        'server',
        'server_api_key'
    ]

    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        # Check for 'server' and 'server_api_key' specifically
        for key, default_value in expected_parameters.items():
            value = config.get(key)
            if not value or value == default_value:
                print()
                print(f"Parameter '{key}' is missing or set to its default value.")
                return False

        # Check for the existence of all parameter names
        for param in all_expected_names:
            parts = param.split('.')
            temp_config = config
            for part in parts:
                if part in temp_config:
                    temp_config = temp_config[part]
                else:
                    print()
                    print(f"Parameter '{param}' does not exist.")
                    return False

    except Exception as e:
        print(f"Error reading or parsing {config_path}: {e}")
        return False

    return True


def load_yaml(file_path):
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except:
        #logging.error(f"Error loading YAML file {file_path}: {e}")
        return None

def save_yaml(data, file_path):
    try:
        with open(file_path, 'w') as file:
            yaml.safe_dump(data, file)
    except yaml.YAMLError as e:
        logging.error(f"Error saving YAML file {file_path}: {e}")
        
def version():
    version = 0.92
    return version

def download_remote_config(server, api_key, group):
    url = f'{server}/api/clients/{group}'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {"version":version(), "time":f"{current_time}"}
        r = requests.post(url,json=data, headers=headers, verify=False, timeout=5)
        r.raise_for_status()
        
        
        remote_config = r.json()
        local_config_path = os.path.join(CONFIG_DIRECTORY, CONFIG_REMOTE)
        existing_config = load_yaml(local_config_path)
    
        if existing_config != remote_config or {}:
            save_yaml(remote_config, local_config_path)
            logging.info("[nettemp client] Remote configuration updated.")
            return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


# def remote_config_enabled():
#     config = load_yaml(os.path.join(CONFIG_DIRECTORY, CONFIG_MAIN))
#     return config and config.get("remote_config", {}).get("enabled", False)

def file_md5_hash(file_path):
    try:
        with open(file_path, 'rb') as file:
            return hashlib.md5(file.read()).hexdigest()
    except FileNotFoundError:
        return None 

config_main = os.path.join(CONFIG_DIRECTORY, CONFIG_MAIN)
if not check_config(config_main):
    exit()

# Your drivers function here

def drivers(config):

# exception for ds2482
    try:
      if config["w1_kernel"]["enabled"] and config["w1_kernel"]["read_in_sec"]:
        try:
          import drivers.ds2482
        except Exception as e:
          pass
          #print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))
    except Exception as e:
      pass
      #print("\n[WARN] Error \n\tArgs: '%s'" % (str(e.args)))

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
        {"name": "sdm120", "module": "drivers.sdm120", "extra_args": []},
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
            else:
                sched.add_job(
                    getattr(module, sensor_name),
                    'interval',
                    seconds=config[sensor_name]["read_in_sec"],
                    args=extra_args
                )
      

# Main logic
def main():
    # Load main and local configuration hashes
    config_hashes = {
        CONFIG_MAIN: file_md5_hash(os.path.join(CONFIG_DIRECTORY, CONFIG_MAIN)),
        # CONFIG_LOCAL: file_md5_hash(os.path.join(CONFIG_DIRECTORY, CONFIG_LOCAL)),
        CONFIG_REMOTE: file_md5_hash(os.path.join(CONFIG_DIRECTORY, CONFIG_REMOTE))
    }
    
    # Attempt to load remote config, fallback to local config if unavailable
    config = load_yaml(os.path.join(CONFIG_DIRECTORY, CONFIG_REMOTE)) #or load_yaml(os.path.join(CONFIG_DIRECTORY, CONFIG_LOCAL))
    if config:
        drivers(config)
    else:
        logging.error("[nettemp client] Unable to load remote.conf")

    while True:
        
        # Check if configurations have changed
        new_hashes = {
            CONFIG_MAIN: file_md5_hash(os.path.join(CONFIG_DIRECTORY, CONFIG_MAIN)),
            # CONFIG_LOCAL: file_md5_hash(os.path.join(CONFIG_DIRECTORY, CONFIG_LOCAL)),
            CONFIG_REMOTE: file_md5_hash(os.path.join(CONFIG_DIRECTORY, CONFIG_REMOTE))
        }
        
        # If any configuration has changed, restart the daemon
        if new_hashes != config_hashes:
            logging.info("[nettemp client] Configuration changed, restarting.")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            # Optionally, check for remote configuration updates
            #if remote_config_enabled():
            config_main = load_yaml(os.path.join(CONFIG_DIRECTORY, CONFIG_MAIN))
            try:
                group = config["group"]
            except:
                group = socket.gethostname()
            download_remote_config(config_main["server"], config_main["server_api_key"], config_main.get("group", group))
                
        time.sleep(60)  # Check every minute
        
if __name__ == "__main__":
    main()

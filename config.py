#!/usr/bin/env python

import os, yaml

def configInit():
    # configd = {
    #      'w1_kernel': {'enabled': False, 'read_in_sec': 60, 'info': 'DS18B20 over USB DS9490R, I2C DS2482'}, 
    #      'w1_kernel_gpio': {'enabled': False, 'read_in_sec': 60, 'info':'gpio4, turn off w1_kernel and do system reboot. Add dtoverlay=w1-gpio,gpiopin=x to /boot/config.txt, do system reboot.'}, 
    #      'system': {'enabled': True, 'read_in_sec': 60}, 
    #      'tmp102': {'enabled': False, 'read_in_sec': 60}, 
    #      'rpi': {'enabled': False, 'read_in_sec': 60}, 
    #      'lm_sensors': {'enabled': False, 'read_in_sec': 60},
    #      'bmp180': {'enabled': False, 'read_in_sec': 60}, 
    #      'bme280': {'enabled': False, 'read_in_sec': 60}, 
    #      'htu21d': {'enabled': False, 'read_in_sec': 60}, 
    #      'bh1750': {'enabled': False, 'read_in_sec': 60}, 
    #      'vl53l0x': {'enabled': False, 'read_in_sec': 60}, 
    #      'adxl345': {'enabled': False, 'read_in_sec': 60}, 
    #      'hih6130': {'enabled': False, 'read_in_sec': 60}, 
    #      'tsl2561': {'enabled': False, 'read_in_sec': 60}, 
    #      'mpl3115a2': {'enabled': False, 'read_in_sec': 60}, 
    #      'dht11': {'enabled': False, 'read_in_sec': 60, 'gpio_pin': 4, 'info':'minimum read interval 60sec'}, 
    #      'dht22': {'enabled': False, 'read_in_sec': 60, 'gpio_pin': 4, 'info':'minimum read interval 60sec'},
    #      'ping' : {'enabled': True, 'read_in_sec': 60, 'hosts':['wp.pl','https://google.com']},
    #      'sdm120': {'enabled': False, 'read_in_sec': 60},
    #     }

    config = {
      'server': 'https://default_server',
      'server_api_key': 'default_key',
      'remote_config': {'enabled': 'true'},
      'group': 'nettemp_client1',
      'mqtt_server':'empty',
      'mqtt_port': 1883,
      'mqtt_username': 'empty',
      'mqtt_password': 'empty',
      }

    config_file_path = "config.conf"

    # Check if config.conf exists
    if not os.path.exists(config_file_path):
        print("[ config ] NEW config creating!")
        with open(config_file_path, 'w') as yamlfile:
            yaml.dump(config, yamlfile, default_flow_style=False)
    else:
        print("[ config ] Config already exists! Checking for missing keys...")
        
        # Load the existing configuration
        with open(config_file_path, 'r') as yamlfile:
            existing_config = yaml.load(yamlfile, Loader=yaml.FullLoader) or {}
        
        # Update the existing configuration with any missing keys
        updated = False
        for key, value in config.items():
            if key not in existing_config:
                print(f"Adding missing key: {key}")
                existing_config[key] = value
                updated = True
        
        # If there were any updates, write the updated configuration back to the file
        if updated:
            with open(config_file_path, 'w') as yamlfile:
                yaml.dump(existing_config, yamlfile, default_flow_style=False)
                print("[ config ] Config updated with missing keys.")
        else:
            print("[ config ] No updates needed.")
       

configInit()
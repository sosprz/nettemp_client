#!/usr/bin/env python

import os, yaml

def configInit():
    configd = {
         'w1_kernel': {'enabled': False, 'read_in_sec': 60, 'info': 'DS18B20 over USB DS9490R, I2C DS2482'}, 
         'w1_kernel_gpio': {'enabled': False, 'read_in_sec': 60, 'info':'gpio4, turn off w1_kernel and do system reboot. Add dtoverlay=w1-gpio,gpiopin=x to /boot/config.txt, do system reboot.'}, 
         'system': {'enabled': True, 'read_in_sec': 60}, 
         'tmp102': {'enabled': False, 'read_in_sec': 60}, 
         'rpi': {'enabled': False, 'read_in_sec': 60}, 
         'lm_sensors': {'enabled': False, 'read_in_sec': 60},
         'bmp180': {'enabled': False, 'read_in_sec': 60}, 
         'bme280': {'enabled': False, 'read_in_sec': 60}, 
         'htu21d': {'enabled': False, 'read_in_sec': 60}, 
         'bh1750': {'enabled': False, 'read_in_sec': 60}, 
         'vl53l0x': {'enabled': False, 'read_in_sec': 60}, 
         'adxl345': {'enabled': False, 'read_in_sec': 60}, 
         'hih6130': {'enabled': False, 'read_in_sec': 60}, 
         'tsl2561': {'enabled': False, 'read_in_sec': 60}, 
         'mpl3115a2': {'enabled': False, 'read_in_sec': 60}, 
         'dht11': {'enabled': False, 'read_in_sec': 60, 'gpio_pin': 4, 'info':'minimum read interval 60sec'}, 
         'dht22': {'enabled': False, 'read_in_sec': 60, 'gpio_pin': 4, 'info':'minimum read interval 60sec'},
         'ping' : {'enabled': True, 'read_in_sec': 60, 'hosts':['wp.pl','https://google.com']}
        }

    config = {
      'server': 'https://default_server',
      'server_api_key': 'default_key',
      'remote_config': {'enabled': 'true'},
      'group': 'nettemp_client1'
      }

    if (os.path.exists("local.conf") == False):
      print("[  nettemp client  ][ config ] NEW driver configd creating!")
      with open('local.conf', 'a+') as yamlfile:
         data = yaml.dump(configd, yamlfile)
    else:
      print("[  nettemp client  ][ config ] Configd already exist!")

    if (os.path.exists("config.conf") == False):
      print("[  nettemp client  ][ config ] NEW configd creating!")
      with open('config.conf', 'a+') as yamlfile:
         data = yaml.dump(config, yamlfile)
    else:
      print("[  nettemp client  ][ config ] Configd already exist!")
       

configInit()
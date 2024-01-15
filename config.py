import os, yaml

def configInit():
    configd = [
        {'w1_kernel': {'enabled': False, 'read_in_sec': 60}, 
         'w1_kernel_gpio': {'enabled': False, 'read_in_sec': 60}, 
         'system': {'enabled': True, 'read_in_sec': 60}, 
         'tmp102': {'enabled': False, 'read_in_sec': 60}, 
         'rpi': {'enabled': False, 'read_in_sec': 60}, 
         'lm_sensors': {'enabled': True, 'read_in_sec': 60},
         'bmp180': {'enabled': False, 'read_in_sec': 60}, 
         'bme280': {'enabled': False, 'read_in_sec': 60}, 
         'htu21d': {'enabled': False, 'read_in_sec': 60}, 
         'bh1750': {'enabled': False, 'read_in_sec': 60}, 
         'vl53l0x': {'enabled': False, 'read_in_sec': 60}, 
         'adxl345': {'enabled': False, 'read_in_sec': 60}, 
         'hih6130': {'enabled': False, 'read_in_sec': 60}, 
         'tsl2561': {'enabled': False, 'read_in_sec': 60}, 
         'mpl3115a2': {'enabled': False, 'read_in_sec': 60}, 
         'dht11': {'enabled': False, 'read_in_sec': 60, 'gpio_pin': 4}, 
         'dht22': {'enabled': False, 'read_in_sec': 60, 'gpio_pin': 4}}
    ]

    confg = [
       {'server_ip': 'nettemp.pslocal.pl',
        'server_api_key': 'y8k76HDjmuQqJDKIaFwf8rk55sa8jIh1zCzZJ6sJZ8c'}
    ]

    if (os.path.exists("configd.conf") == False):
      print("[ nettemp ][ config ] NEW driver configd creating!")
      with open('configd.conf', 'a+') as yamlfile:
         data = yaml.dump(configd, yamlfile)
    else:
      print("[ nettemp ][ config ] Configd already exist!")

    if (os.path.exists("config.conf") == False):
      print("[ nettemp ][ config ] NEW configd creating!")
      with open('config.conf', 'a+') as yamlfile:
         data = yaml.dump(config, yamlfile)
    else:
      print("[ nettemp ][ config ] Configd already exist!")
       
    #with open("config.conf", "r") as yamlfile:
    # data = yaml.load(yamlfile, Loader=yaml.FullLoader)
    #print("Read successful")
    #print(data)

configInit()
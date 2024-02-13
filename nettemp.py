import requests
requests.packages.urllib3.disable_warnings() 
import yaml, json, os
import logging

class insert:
  def __init__(self, rom, type, value, name):
    self.logger = logging.getLogger(self.__class__.__name__)
    self.rom = rom
    self.type = type
    self.value = value
    self.name = name

  def request(self):

    config_file = open("config.conf")
    config = yaml.load(config_file, Loader=yaml.FullLoader)
    server = config["server"]
    server_api_key = config["server_api_key"]
    group = config["group"]
    rom=group+self.rom
    name=self.name

    data = [{"rom":rom,"type":self.type, "device":"","value":self.value,"name":name, "group":group}]
    self.logging.debug(data)
    print(data)
    try:
        url = f'{server}'
        r = requests.post(url,headers={'Content-Type':'application/json', 'Authorization': f'Bearer {server_api_key}'},json=data, verify=False)
        self.logging.info("[  nettemp client  ] Sensor %s value: %s" % (self.rom, self.value))
    except:
       self.logging.info("[  nettemp client  ][ cannot connect to server ] Sensor %s value: %s" % (self.rom, self.value))

class insert2:
  def __init__(self, data):
    self.data = data

  def request(self):
    config_file = open("config.conf")
    config = yaml.load(config_file, Loader=yaml.FullLoader)
    server = config["server"]
    server_api_key = config["server_api_key"]
    group = config["group"]
  
    data = self.data
    self.ogging.debug(data)
    print(data)
    for d in data:
      d["group"] = group
      d['rom'] = str(group) + d['rom']
  
    try:
      url = f'{server}'
      r = requests.post(url,headers={'Content-Type':'application/json', 'Authorization': f'Bearer {server_api_key}'},json=data, verify=False, timeout=5)
      self.logging.info(f"[  nettemp client  ][ data package ] ")
    except:
      self.logging.info(f"[  nettemp client  ][ cannot connect to server ] ")


import requests
import inspect
requests.packages.urllib3.disable_warnings() 
import yaml, json, os, socket
from mqtt import send_to_mqtt_broker
import logging

log_level = logging.INFO
logging.basicConfig(level=log_level, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class insert:
  def __init__(self, rom, type, value, name):
    self.rom = rom
    self.type = type
    self.value = value
    self.name = name

  def request(self):

    config_file = open("config.conf")
    config = yaml.load(config_file, Loader=yaml.FullLoader)
    server = config["server"]
    server_api_key = config["server_api_key"]
    
    try:
      group = config["group"]
    except:
      group = socket.gethostname()
      
    rom=group+self.rom
    name=self.name

    data = [{"rom":rom,"type":self.type, "device":"","value":self.value,"name":name, "group":group}]
    try:
        url = f'{server}'
        r = requests.post(url,headers={'Content-Type':'application/json', 'Authorization': f'Bearer {server_api_key}'},json=data, verify=False, timeout=5),
        print(" Sensor %s value: %s" % (self.rom, self.value))
    except:
        print("[ cannot connect to server ] Sensor %s value: %s" % (self.rom, self.value))
    
    try:
        data = str(data)
        send_to_mqtt_broker(data)
    except:
        pass

class insert2:
  def __init__(self, data):
    self.data = data

  def request(self):
    dir = os.path.dirname(os.path.abspath(__file__))
    #parent_dir = os.path.dirname(dir)
    config = "config.conf"
    config_file = os.path.join(dir, config)
    config_file = open(config_file)

    config = yaml.load(config_file, Loader=yaml.FullLoader)
    server = config["server"]
    server_api_key = config["server_api_key"]
    
    try:
      group = config["group"]
    except:
      group = socket.gethostname()
  
    data = self.data
    
    
    for d in data:
      d["group"] = group
      d['rom'] = str(group) + d['rom']
      
    stack = inspect.stack()
    topic = stack[1].function # function name 
  
    try:
      url = f'{server}'
      r = requests.post(url,headers={'Content-Type':'application/json', 'Authorization': f'Bearer {server_api_key}'},json=data, verify=False, timeout=5)
      if r:
        logging.info(f"[ data package sent] ")
    except:
      logging.info(f"[ cannot connect to server ] ")
    
    try:
        data = data
        group = str(group)
        topic = str(topic)
        send_to_mqtt_broker(group, topic, data)
    except:
        pass


import requests
requests.packages.urllib3.disable_warnings() 
import yaml

class insert:
  def __init__(self, rom, type, value, name, group):
    self.rom = rom
    self.type = type
    self.value = value
    self.name = name
    self.group = group

  def request(self):

    config_file = open("config.conf")
    config = yaml.load(config_file, Loader=yaml.FullLoader)
    server_ip = config["server_ip"]
    server_api_key = config["server_api_key"]

    data = [{"rom":self.rom,"type":self.type, "device":"","value":self.value,"name":self.name, "group":self.group}]
    try:
        url = f'https://{server_ip}'
        r = requests.post(url,headers={'Content-Type':'application/json', 'Authorization': f'Bearer {server_api_key}'},json=data, verify=False)
        print (r.content)
        print("[ nettemp client ] Sensor %s value: %s" % (self.rom, self.value))
    except:
      print("[ nettemp client ] [cannot connect to local] Sensor %s value: %s" % (self.rom, self.value))
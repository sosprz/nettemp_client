import requests
requests.packages.urllib3.disable_warnings() 
import yaml, socket, json, os

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
    server = config["server"]
    server_api_key = config["server_api_key"]

    data = [{"rom":self.rom,"type":self.type, "device":"","value":self.value,"name":self.name, "group":self.group}]
    try:
        url = f'{server}'
        r = requests.post(url,headers={'Content-Type':'application/json', 'Authorization': f'Bearer {server_api_key}'},json=data, verify=False)
        print (r.content)
        print("[ nettemp client ] Sensor %s value: %s" % (self.rom, self.value))
    except:
      print("[ nettemp client ] [cannot connect to local] Sensor %s value: %s" % (self.rom, self.value))

class insert2:
  def __init__(self, data):
    self.data = data

  def request(self):
    config_file = open("config.conf")
    config = yaml.load(config_file, Loader=yaml.FullLoader)
    server = config["server"]
    server_api_key = config["server_api_key"]

    data = self.data
    try:
      url = f'{server}'
      r = requests.post(url,headers={'Content-Type':'application/json', 'Authorization': f'Bearer {server_api_key}'},json=data, verify=False)
      print(f"[ nettemp client ] {data}")
    except:
      print(f"[ nettemp client ] [cannot connect to local] {data}")

def remote_config():
    config_file = open("config.conf")
    config = yaml.load(config_file, Loader=yaml.FullLoader)
    server = config["server"]
    server_api_key = config["server_api_key"]
    group = socket.gethostname()

    try:
      url = f'{server}/api/clients/{group}'
      r = requests.get(url,headers={'Content-Type':'application/json', 'Authorization': f'Bearer {server_api_key}'},verify=False)
      config = r.json()

      temp_file = 'temp_remote.conf'
      remote_file = 'remote.conf'

      with open(temp_file, 'w+') as yamlfile:
         data = yaml.dump(config, yamlfile)

      from deepdiff import DeepDiff

      def yaml_as_dict(my_file):
          my_dict = {}
          with open(my_file, 'r') as fp:
              docs = yaml.safe_load_all(fp)
              for doc in docs:
                  for key, value in doc.items():
                      my_dict[key] = value
          return my_dict

      if not os.path.isfile(remote_file):
        with open('remote.conf', 'w+') as yamlfile:
          data = yaml.dump(config, yamlfile)
        print("[ nettemp client ] [ remote config saved ]")
        return True
      else:
        a = yaml_as_dict(temp_file)
        b = yaml_as_dict(remote_file)
        ddiff = DeepDiff(a, b, ignore_order=True)
        if ddiff:
          print(f"[ nettemp client ] [ new remote config: {ddiff} ]")
          return True
        else:
          return False      
      
    except:
      print("[ nettemp client ] [ cannot connect or no config ]")
      return False
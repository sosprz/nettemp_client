import requests
requests.packages.urllib3.disable_warnings() 
import yaml, socket, json, os

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
    group = socket.gethostname()
    rom=group+self.rom
    name=group+self.name

    data = [{"rom":rom,"type":self.type, "device":"","value":self.value,"name":name, "group":group}]
    try:
        url = f'{server}'
        r = requests.post(url,headers={'Content-Type':'application/json', 'Authorization': f'Bearer {server_api_key}'},json=data, verify=False)
        print("[ nettemp client ] Sensor %s value: %s" % (self.rom, self.value))
    except:
      print("[ nettemp client ][ cannot connect to server ] Sensor %s value: %s" % (self.rom, self.value))

class insert2:
  def __init__(self, data):
    self.data = data

  def request(self):
    config_file = open("config.conf")
    config = yaml.load(config_file, Loader=yaml.FullLoader)
    server = config["server"]
    server_api_key = config["server_api_key"]
    group = socket.gethostname()
  
    data = self.data
    for d in data:
      d["group"] = group
      d['rom'] = str(group) + d['rom']
      d['name'] = str(group) + d['name']

    try:
      url = f'{server}'
      r = requests.post(url,headers={'Content-Type':'application/json', 'Authorization': f'Bearer {server_api_key}'},json=data, verify=False)
      print(f"[ nettemp client ][ data package ] {data}")
    except:
      print(f"[ nettemp client ][ cannot connect to server ] {data}")

def download_remote_config():
    from deepdiff import DeepDiff

    def yaml_as_dict(my_file):
      my_dict = {}
      with open(my_file, 'r') as fp:
          docs = yaml.safe_load_all(fp)
          for doc in docs:
              for key, value in doc.items():
                  my_dict[key] = value
      return my_dict
      
    config_file = open("config.conf")
    config = yaml.load(config_file, Loader=yaml.FullLoader)
    server = config["server"]
    server_api_key = config["server_api_key"]
    group = socket.gethostname()

    try:
      url = f'{server}/api/clients/{group}'
      r = requests.get(url,headers={'Content-Type':'application/json', 'Authorization': f'Bearer {server_api_key}'},verify=False)
      remote_joson = r.json()
      print(f"[ nettemp client ][ connection to remote server: {r.status_code} ]")

      temp_file = 'temp_remote.conf'
      local_file = 'remote.conf'

      # 1. get remote json, convert yaml and save to temp file
      with open(temp_file, 'w+') as yamlfile:
         data = yaml.dump(remote_joson, yamlfile)
   
      # 2. if remote.conf not exist create yaml from json request
      if not os.path.isfile(local_file):
        with open('remote.conf', 'w+') as yamlfile:
          data = yaml.dump(remote_joson, yamlfile)
        print("[ nettemp client ][ remote config saved ]")
        return True
      else:
        # 3. if remote exist check if temp is newer
        b = yaml_as_dict(temp_file)
        a = yaml_as_dict(local_file)
        ddiff = DeepDiff(a, b, ignore_order=True)
        if ddiff:
          # if diff exist write new remote.conf
          print(f"[ nettemp client ][ new remote config: {ddiff} ]")
          os.remove(local_file)
          os.rename(temp_file, local_file)
          return True
        else:
          os.remove(temp_file)
          return False      
      
    except:
      print("[ nettemp client ][ Failed to connect or remote not configured. ]")
      return False
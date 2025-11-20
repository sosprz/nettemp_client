
import subprocess, json, socket

def lm_sensors(config_dict):
  try:
    output = subprocess.check_output("/usr/bin/sensors -j", shell=True)
    output = output.decode("utf-8")
    lmdata = json.loads(output)
    
    data = []
    for item in lmdata:
        for name in lmdata[item]:
            for sens in lmdata[item][name]:
                if name != "Adapter" and sens == "temp1_input":
                    print(item, name, lmdata[item][name][sens])
                    value = '{0:0.1f}'.format(lmdata[item][name][sens])
                    rom = '_'+item+'_'+name
                    type = 'temp'
                    name = item+'_'+name
                    data.append({"rom":rom,"type":type, "value":value,"name":name})

    return data

  except:
     print("NO LM-SENSORS")




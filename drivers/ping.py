import yaml, socket
from nettemp import insert2
import json
import pingparsing, requests, time
requests.packages.urllib3.disable_warnings() 

def ping():
    print("[ nettemp ][ ping ] start")

    group = socket.gethostname()
    data = []

    try:
        config = yaml.load(open("remote.conf"), Loader=yaml.FullLoader)
    except:
        config = yaml.load(open("drivers.conf"), Loader=yaml.FullLoader)

    print(config["ping"]["hosts"])

    ping_parser = pingparsing.PingParsing()
    transmitter = pingparsing.PingTransmitter()
    for name in config["ping"]["hosts"]:
        
        if name.startswith(('http://', 'https://')):
            start = time.perf_counter()
            try:
                r = requests.get(name, verify=False)
                code = r.status_code
            except:
                code = 0
                
            request_time = time.perf_counter() - start
            
            if code == 200: 
                value = '{0:0.2f}'.format(request_time)
            else:
                value = 0
            type='url'
        
        else:
            transmitter.destination = name
            transmitter.count = 3
            result = transmitter.ping()
            out = json.dumps(ping_parser.parse(result).as_dict(), indent=4)
            jout = json.loads(out)
    
            if jout['rtt_avg']:
                value = jout['rtt_avg']
                value = '{0:0.2f}'.format(value)
            else:
                value = 0
            type='host'
    
        print(f"[ nettemp ][ ping ] {name} Request completed in {value}ms")

        name = name.replace("https://","")
        name = name.replace("http://","")
        rom=group+'_'+name
        data.append({"rom":rom,"type":type, "value":value,"name":name, "group":group})

    data=insert2(data)
    data.request()
    print("[ nettemp ][ ping ] End")

import yaml, socket
from nettemp import insert2
import json
import pingparsing

def ping():
    print("PING")
    try:

        group = socket.gethostname()
        data = []

        try:
        config = yaml.load(open("remote.conf"), Loader=yaml.FullLoader)
        except:
        config = yaml.load(open("configd.conf"), Loader=yaml.FullLoader)

        print(config["ping"]["hosts"])

        ping_parser = pingparsing.PingParsing()
        transmitter = pingparsing.PingTransmitter()
        for name in config["ping"]["hosts"]:
            transmitter.destination = name
            transmitter.count = 3
            result = transmitter.ping()
            out = json.dumps(ping_parser.parse(result).as_dict(), indent=4)
            jout = json.loads(out)
            value = '{0:0.2f}'.format(jout['rtt_avg'])
            print(name, value)
            rom=group+'_'+name
            type='host'
            data.append({"rom":rom,"type":type, "value":value,"name":name, "group":group})

        data=insert2(data)
        data.request()
    except:
        print("No system")

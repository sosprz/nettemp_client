import logging
import yaml
import pingparsing
import requests
import time
import json
import os
from concurrent.futures import ThreadPoolExecutor
requests.packages.urllib3.disable_warnings()

def perform_ping(name):
    ping_parser = pingparsing.PingParsing()
    transmitter = pingparsing.PingTransmitter()
    data = None

    if name.startswith(('http://', 'https://')):
        start = time.perf_counter()
        try:
            r = requests.get(name, verify=False, timeout=5)
            code = r.status_code
        except:
            code = 0

        request_time = time.perf_counter() - start

        if code in [200]:
            value = '{0:0.2f}'.format(request_time)
        else:
            value = 0
        type = 'url'

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
        type = 'host'

    name4r = name.replace("://", "_")
    rom = '_' + type + '_' + name4r

    data = {"rom": rom, "type": type, "value": value, "name": name}
    logging.info(f"[ ping ] {name} Request completed in {value}ms")

    return data

def ping(config_dict):
    logging.info("[ ping ] start")
    hosts = config_dict.get("hosts")
    
    # Use ThreadPoolExecutor to perform ping in parallel
    with ThreadPoolExecutor(max_workers=len(hosts)) as executor:
        results = list(executor.map(perform_ping, hosts))

    # Filter out None results if any
    data = [result for result in results if result is not None]

    if data:
        return data
        # Assuming insert2 is a function that processes the data list
        # And assuming data.request() should be calling a method on the result of insert2

    logging.info("[ ping ] End")


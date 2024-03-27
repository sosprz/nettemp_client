#!/usr/bin/env python3

import argparse
import json
import sdm_modbus
import socket, random, os, yaml
from nettemp import insert2
import logging

def sdm120():
    logging.info("sdm120")
    try:
        model = "SDM120"
        
        dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(dir)
        remote_config = os.path.join(parent_dir, "remote.conf")
        config = yaml.load(open(remote_config), Loader=yaml.FullLoader)
        
        port = config["sdm120"]["port"]
        unit = config["sdm120"]["unit"]
         
        meter = sdm_modbus.SDM120(
            device=port,
            timeout=1,
            parity="N",
            unit=unit
        )
        data = []
        
        v = meter.read("voltage")
        c =  meter.read("current")
        pa = meter.read("power_active")

      
        v = f"{v:.2f}"
        c = f"{c:.2f}"
        pa = f"{pa:.2f}"

        logging.info(f"SDM120 {v}V {c}A {pa}W")
        
        for type, value in {"volt":v, "amps":c, "watt":pa}.items():
            value = value
            rom = f"_{model}_{unit}_{type}"
            type = f"{type}"
            name = f"{model} {type}"
            data.append({"rom":rom,"type":type, "value":value,"name":name})

        data=insert2(data)
        data.request()
        
        meter.disconnect()
    except:
        logging.info("sdm 120 error")
        

#print(f"{meter}:")

# print("\nInput Registers:")

# for k, v in meter.read_all(sdm_modbus.registerType.INPUT).items():
#     address, length, rtype, dtype, vtype, label, fmt, batch, sf = meter.registers[k]

#     if type(fmt) is list or type(fmt) is dict:
#         print(f"\t{label}: {fmt[str(v)]}")
#     elif vtype is float:
#         print(f"\t{label}: {v:.2f}{fmt}")
#     else:
#         print(f"\t{label}: {v}{fmt}")

# print("\nHolding Registers:")

# for k, v in meter.read_all(sdm_modbus.registerType.HOLDING).items():
#     address, length, rtype, dtype, vtype, label, fmt, batch, sf = meter.registers[k]

#     if type(fmt) is list:
#         print(f"\t{label}: {fmt[v]}")
#     elif type(fmt) is dict:
#         print(f"\t{label}: {fmt[str(v)]}")
#     elif vtype is float:
#         print(f"\t{label}: {v:.2f}{fmt}")
#     else:
#         print(f"\t{label}: {v}{fmt}")

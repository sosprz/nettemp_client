#!/usr/bin/env python3

import argparse
import json
import sdm_modbus
import socket, random, os, yaml
import logging

def sdm120(config_dict):
    try:
        model = "SDM120"
        
        port = config_dict.get("port")
        unit = config_dict.get("unit")
         
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
        
        meter.disconnect()

        return data
        
    except:
        logging.info("sdm 120 error")

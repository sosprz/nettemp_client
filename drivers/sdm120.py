#!/usr/bin/env python3

import argparse
import json
import logging

try:
    import sdm_modbus
    SDM_MODBUS_AVAILABLE = True
except ImportError as e:
    SDM_MODBUS_AVAILABLE = False
    logging.warning(f"sdm_modbus import failed: {e}. Install with: pip install sdm-modbus")

def sdm120(config_dict):
    if not SDM_MODBUS_AVAILABLE:
        logging.warning("SDM120: sdm_modbus library not available")
        return []
    
    meter = None
    try:
        model = "SDM120"
        
        port = config_dict.get("port")
        unit = config_dict.get("unit")
        baudrate = config_dict.get("baudrate", 9600)
        parity = config_dict.get("parity", "N")
        timeout = config_dict.get("timeout", 1)
        
        if not port or unit is None:
            logging.error("SDM120: Missing 'port' or 'unit' in config")
            return []
        
        logging.debug(f"SDM120: Connecting to {port}, unit={unit}, baud={baudrate}, parity={parity}")
         
        meter = sdm_modbus.SDM120(
            device=port,
            timeout=timeout,
            baudrate=baudrate,
            parity=parity,
            unit=unit
        )
        
        # Test connection by reading voltage
        v = meter.read("voltage")
        if v is None:
            logging.error(f"SDM120: No response from meter at {port}, unit {unit}. Check wiring, unit ID, and baudrate.")
            return []
        
        c = meter.read("current")
        pa = meter.read("power_active")
        
        # Check if readings are valid
        if c is None or pa is None:
            logging.warning(f"SDM120: Partial read failure (voltage={v}, current={c}, power={pa})")
            if v is None:
                return []

        v_str = f"{v:.2f}" if v is not None else "0.00"
        c_str = f"{c:.2f}" if c is not None else "0.00"
        pa_str = f"{pa:.2f}" if pa is not None else "0.00"

        logging.info(f"SDM120 unit {unit}: {v_str}V {c_str}A {pa_str}W")
        
        data = []
        for type, value in {"volt": v_str, "amps": c_str, "watt": pa_str}.items():
            rom = f"{model}_{unit}_{type}"
            name = f"{model} {type}"
            data.append({"rom": rom, "type": type, "value": value, "name": name})
        
        return data
        
    except Exception as e:
        logging.error(f"SDM120 error: {e}")
        return []
    
    finally:
        if meter:
            try:
                meter.disconnect()
            except:
                pass

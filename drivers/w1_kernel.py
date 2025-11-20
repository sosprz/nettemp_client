import random
import logging

# Track whether DS2482 has been initialized
_ds2482_initialized = False

def w1_kernel(config_dict):
    """Read DS18B20 sensors via w1thermsensor.

    Returns a list of dicts: {rom, type, value, name}.

    Config options:
        - ds2482: (optional, default: false) If true, initializes DS2482 I2C-to-1Wire bridge
                  on first call. If false or omitted, uses standard kernel GPIO 1-Wire.
    """
    global _ds2482_initialized

    # Check if DS2482 initialization is needed
    if config_dict.get('ds2482') and not _ds2482_initialized:
        logging.info("DS2482 mode detected - initializing DS2482 bridge...")
        try:
            from drivers.ds2482 import ds2482_init
            if ds2482_init(config_dict):
                _ds2482_initialized = True
                logging.info("DS2482 initialized successfully")
            else:
                logging.error("DS2482 initialization failed - continuing anyway")
        except Exception as e:
            logging.error(f"DS2482 initialization error: {e}")

    try:
        from w1thermsensor import W1ThermSensor
    except Exception as e:
        # w1thermsensor not available on this system
        print("No w1_kernel (w1thermsensor import failed):", e)
        return []

    data = []
    try:
        for sensor in W1ThermSensor.get_available_sensors():
            r = random.randint(10000, 99999)
            try:
                value = sensor.get_temperature()
            except Exception as e:
                print("w1 read error for sensor", getattr(sensor, 'id', None), e)
                continue
            rom = '_28_' + str(sensor.id)
            type_ = 'temp'
            name = 'DS18B20-' + str(r)
            data.append({"rom": rom, "type": type_, "value": value, "name": name})
    except Exception as e:
        print("w1_kernel iteration error:", e)

    return data

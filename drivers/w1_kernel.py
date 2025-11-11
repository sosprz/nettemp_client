import random

def w1_kernel(config_dict):
    """Read DS18B20 sensors via w1thermsensor.

    Returns a list of dicts: {rom, type, value, name}.
    """
    print("w1_kernel")

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

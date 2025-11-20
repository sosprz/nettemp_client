import socket, random

def w1_kernel_gpio(config_dict):
\tprint("w1_kernel_gpio")
\ttry:
\t\tfrom w1thermsensor import W1ThermSensor

\t\tdata = []

\t\tfor sensor in W1ThermSensor.get_available_sensors():
\t\t\tr = random.randint(10000,99999)
\t\t\tvalue = sensor.get_temperature()
\t\t\trom = '_28_'+sensor.id
\t\t\ttype = 'temp'
\t\t\tname = 'DS18b20-'+str(r)
\t\t\tdata.append({"rom":rom,"type":type, "value":value,"name":name})

\t\treturn data

\texcept Exception:
\t\tprint("No w1_kernel")
\t\treturn []

import os
import subprocess
import time

# Check for the existence of i2c devices and assign nbus accordingly
if os.path.exists('/dev/i2c-0'):
    nbus = "i2c-0"
elif os.path.exists('/dev/i2c-1'):
    nbus = "i2c-1"
elif os.path.exists('/dev/i2c-2'):
    nbus = "i2c-2"
elif os.path.exists('/dev/i2c-3'):
    nbus = "i2c-3"
else:
    nbus = None

if nbus is not None:
    # Load kernel modules
    subprocess.run(['modprobe', 'ds2482'])
    subprocess.run(['modprobe', 'w1-therm'])
    
    # Give time for the modules to load
    time.sleep(3)
    
    # Write to the new_device file for each address
    addresses = ['0x18', '0x19', '0x1a', '0x1b']
    for address in addresses:
        with open(f'/sys/bus/i2c/devices/{nbus}/new_device', 'w') as f:
            f.write(f'ds2482 {address}')
        time.sleep(3)
    
    # Set w1_master_pullup
    with open('/sys/bus/w1/devices/w1_bus_master1/w1_master_pullup', 'w') as f:
        f.write('0')
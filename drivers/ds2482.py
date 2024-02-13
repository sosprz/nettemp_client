import subprocess
import time
import os

# Assuming the initial setup
nbus = None
for i in range(4):  # Check for the first available i2c bus
    if os.path.exists(f'/dev/i2c-{i}'):
        nbus = f"i2c-{i}"
        break

if nbus is not None:
    # Run commands with 'sudo'
    subprocess.run(['sudo', 'modprobe', 'ds2482'], check=True)
    subprocess.run(['sudo', 'modprobe', 'w1-therm'], check=True)
    
    # Give time for the modules to load
    time.sleep(3)
    
    # Prepare the commands for writing to new_device files
    addresses = ['0x18', '0x19', '0x1a', '0x1b']
    for address in addresses:
        # This part requires the script to be run with sudo for file access permissions
        with open(f'/sys/bus/i2c/devices/{nbus}/new_device', 'w') as f:
            f.write(f'ds2482 {address}')
        time.sleep(3)
    
    # Set w1_master_pullup - also requires sudo to run the script
    with open('/sys/bus/w1/devices/w1_bus_master1/w1_master_pullup', 'w') as f:
        f.write('0')
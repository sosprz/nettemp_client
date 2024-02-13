import subprocess
import os
import time

# Function to find the first available I2C bus
def find_nbus():
    for i in range(6):
        if os.path.exists(f'/dev/i2c-{i}'):
            return f"i2c-{i}"
    return None

# Function to load necessary kernel modules
def load_modules():
    subprocess.run(['sudo', 'modprobe', 'ds2482'], check=True)
    subprocess.run(['sudo', 'modprobe', 'w1-therm'], check=True)

# Function to write to /sys devices
def write_to_sys(device_path, content):
    cmd = f'echo {content} | sudo tee {device_path}'
    subprocess.run(cmd, shell=True, check=True)

# Main function to setup devices
def setup_devices(nbus):
    if nbus:
        load_modules()
        time.sleep(3)  # Give time for the modules to load

        # Writing addresses to the new_device
        addresses = ['0x18', '0x19', '0x1a', '0x1b']
        for address in addresses:
            write_to_sys(f'/sys/bus/i2c/devices/{nbus}/new_device', f'ds2482 {address}')
            time.sleep(3)

        # Setting w1_master_pullup
        write_to_sys('/sys/bus/w1/devices/w1_bus_master1/w1_master_pullup', '0')

# Example usage
nbus = find_nbus()
setup_devices(nbus)
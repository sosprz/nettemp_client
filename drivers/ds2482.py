"""
DS2482 - 1-Wire to I2C Bridge Driver
Initializes DS2482 hardware for use with w1_kernel driver
"""
import subprocess
import os
import time
import logging

def find_i2c_bus():
    """Find the first available I2C bus"""
    for i in range(6):
        if os.path.exists(f'/dev/i2c-{i}'):
            return f"i2c-{i}"
    return None

def load_kernel_modules():
    """Load necessary kernel modules for DS2482"""
    try:
        subprocess.run(['sudo', 'modprobe', 'ds2482'], check=True)
        subprocess.run(['sudo', 'modprobe', 'w1-therm'], check=True)
        logging.info("Loaded ds2482 and w1-therm kernel modules")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to load kernel modules: {e}")
        raise

def write_to_sysfs(device_path, content):
    """Write to /sys filesystem"""
    cmd = f'echo {content} | sudo tee {device_path}'
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to write to {device_path}: {e}")
        raise

def ds2482_init(config_dict=None):
    """
    Initialize DS2482 I2C to 1-Wire bridge
    This function is called once at startup if ds2482 is enabled

    Args:
        config_dict: Optional configuration dictionary

    Returns:
        True if initialization successful, False otherwise
    """
    logging.info("Initializing DS2482 1-Wire bridge...")

    # Find I2C bus
    i2c_bus = find_i2c_bus()
    if not i2c_bus:
        logging.error("No I2C bus found (/dev/i2c-* not available)")
        return False

    logging.info(f"Found I2C bus: {i2c_bus}")

    try:
        # Load kernel modules
        load_kernel_modules()
        time.sleep(3)  # Give time for modules to load

        # Get I2C addresses from config or use defaults
        addresses = config_dict.get('addresses', ['0x18', '0x19', '0x1a', '0x1b']) if config_dict else ['0x18', '0x19', '0x1a', '0x1b']

        # Register DS2482 devices on I2C bus
        for address in addresses:
            try:
                write_to_sysfs(f'/sys/bus/i2c/devices/{i2c_bus}/new_device', f'ds2482 {address}')
                logging.info(f"Registered DS2482 device at {address}")
                time.sleep(3)
            except Exception as e:
                logging.warning(f"Failed to register DS2482 at {address}: {e}")

        # Disable pullup on w1 bus master
        try:
            write_to_sysfs('/sys/bus/w1/devices/w1_bus_master1/w1_master_pullup', '0')
            logging.info("Disabled w1_master_pullup")
        except Exception as e:
            logging.warning(f"Failed to set w1_master_pullup: {e}")

        logging.info("DS2482 initialization complete")
        return True

    except Exception as e:
        logging.error(f"DS2482 initialization failed: {e}")
        return False

def ds2482(config_dict=None):
    """
    Driver function for DS2482 - not used for reading, only for initialization
    This driver doesn't read sensors, it only initializes hardware
    Use w1_kernel driver to read actual sensor values

    Returns empty list as this driver doesn't produce readings
    """
    _ = config_dict  # Unused but required for driver interface
    logging.info("DS2482 driver called - this driver only initializes hardware, use w1_kernel to read sensors")
    return []
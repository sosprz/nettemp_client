"""
Driver loader - Auto-discover and schedule sensor drivers
"""
import importlib
import logging
import yaml
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


class DriverLoader:
    """Load and manage sensor drivers"""

    def __init__(self, drivers_path='drivers', config_file='drivers_config.yaml'):
        self.drivers_path = Path(__file__).parent / drivers_path
        self.config_file = Path(__file__).parent / config_file
        self.loaded_drivers = {}
        self.config = self.load_config()

    def load_config(self):
        """Load driver configuration from YAML file"""
        if not self.config_file.exists():
            logging.warning(f"Config file not found: {self.config_file}")
            return {}

        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
            logging.info(f"Loaded config for {len(config)} drivers")
            return config
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return {}

    def get_enabled_drivers(self):
        """Get list of enabled drivers from config"""
        enabled = []
        for driver_name, driver_config in self.config.items():
            if isinstance(driver_config, dict) and driver_config.get('enabled'):
                enabled.append((driver_name, driver_config))
        return enabled

    def discover_drivers(self):
        """Auto-discover all available drivers"""
        drivers = []

        if not self.drivers_path.exists():
            logging.warning(f"Drivers path not found: {self.drivers_path}")
            return drivers

        for file in self.drivers_path.glob('*.py'):
            if file.name.startswith('_'):
                continue

            driver_name = file.stem
            drivers.append(driver_name)

        logging.info(f"Discovered {len(drivers)} drivers: {', '.join(drivers)}")
        return drivers

    def load_driver(self, driver_name):
        """Load a specific driver module"""
        if driver_name in self.loaded_drivers:
            return self.loaded_drivers[driver_name]

        try:
            module = importlib.import_module(f'drivers.{driver_name}')
            driver_func = getattr(module, driver_name)
            self.loaded_drivers[driver_name] = driver_func
            logging.info(f"Loaded driver: {driver_name}")
            return driver_func
        except ImportError as e:
            logging.error(f"Failed to import driver '{driver_name}': {e}")
            return None
        except AttributeError as e:
            logging.error(f"Driver function '{driver_name}' not found in module: {e}")
            return None

    def run_driver(self, driver_name, config_dict):
        """
        Run a driver with given config

        Args:
            driver_name: Name of the driver (e.g., 'dht22')
            config_dict: Configuration dictionary for the driver

        Returns:
            List of sensor readings or empty list on error
        """
        driver_func = self.load_driver(driver_name)

        if not driver_func:
            return []

        try:
            readings = driver_func(config_dict)
            return readings or []
        except Exception as e:
            logging.error(f"Error running driver '{driver_name}': {e}")
            return []

    def load_drivers_from_config(self, config):
        """
        Load and schedule drivers based on config

        Config format:
        {
            "dht22": {"enabled": true, "read_in_sec": 60, "gpio_pin": 4},
            "system": {"enabled": true, "read_in_sec": 30}
        }

        Returns:
            List of (driver_name, config_dict, interval) tuples for enabled drivers
        """
        enabled_drivers = []

        for driver_name, driver_config in config.items():
            if not isinstance(driver_config, dict):
                continue

            if not driver_config.get('enabled'):
                continue

            # Default to 60 seconds if not provided in config
            read_in_sec = driver_config.get('read_in_sec', 60)
            if not isinstance(read_in_sec, int):
                try:
                    read_in_sec = int(read_in_sec)
                except Exception:
                    logging.warning(f"Driver '{driver_name}' has invalid read_in_sec, skipping")
                    continue

            enabled_drivers.append((driver_name, driver_config, read_in_sec))
            logging.info(f"Enabled driver: {driver_name} (interval: {read_in_sec}s)")

        return enabled_drivers


# Example usage
if __name__ == "__main__":
    loader = DriverLoader()

    # Discover all available drivers
    drivers = loader.discover_drivers()
    print(f"\nAvailable drivers: {drivers}\n")

    # Show enabled drivers from config
    enabled = loader.get_enabled_drivers()
    print(f"Enabled drivers from config: {[d[0] for d in enabled]}\n")

    # Load and test system driver
    if loader.config.get('system', {}).get('enabled'):
        readings = loader.run_driver('system', loader.config['system'])
        print(f"System readings: {readings}")

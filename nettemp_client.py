#!/usr/bin/env python3
"""
Nettemp Client - Production client with local config
Reads drivers_config.yaml and runs enabled drivers on schedule
"""
import sys
import time
import logging
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler

sys.path.insert(0, str(Path(__file__).parent))

from nettemp import CloudClient, insert2
from driver_loader import DriverLoader

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


class NettempClient:
    """Run sensors based on local config and send to cloud"""

    def __init__(self, config_file='config.conf', drivers_config='drivers_config.yaml'):
        self.loader = DriverLoader(config_file=drivers_config)
        self.cloud_client = CloudClient(config_file)
        self.scheduler = BackgroundScheduler({'apscheduler.timezone': 'UTC'})

    def read_and_send(self, driver_name, driver_config):
        """Read sensor and send to cloud"""
        logging.info(f"Reading: {driver_name}")

        # Run driver
        readings = self.loader.run_driver(driver_name, driver_config)

        if not readings:
            logging.warning(f"No readings from {driver_name}")
            return

        # Send data as-is - backend will handle normalization and units
        try:
            sender = insert2(readings)
            sender.request()
            logging.info(f"✓ {driver_name}: Sent {len(readings)} readings")
        except Exception as e:
            logging.error(f"Failed to send {driver_name}: {e}")

    def initialize_hardware(self):
        """Initialize hardware that requires one-time setup"""
        # Check if w1_kernel driver has ds2482 enabled
        w1_config = self.loader.config.get('w1_kernel', {})
        if isinstance(w1_config, dict) and w1_config.get('ds2482'):
            logging.info("DS2482 initialization requested in w1_kernel config")
            try:
                from drivers.ds2482 import ds2482_init
                success = ds2482_init(w1_config)
                if success:
                    logging.info("✓ DS2482 initialized successfully")
                else:
                    logging.error("✗ DS2482 initialization failed")
            except Exception as e:
                logging.error(f"✗ DS2482 initialization error: {e}")

    def start(self):
        """Start scheduled sensor reading"""
        # Run hardware initialization first
        self.initialize_hardware()

        enabled_drivers = self.loader.get_enabled_drivers()

        if not enabled_drivers:
            logging.warning("No enabled drivers in config!")
            return

        logging.info(f"Starting runner with {len(enabled_drivers)} enabled drivers")

        # Schedule each enabled driver
        for driver_name, driver_config in enabled_drivers:
            interval = driver_config.get('read_in_sec', 60)

            self.scheduler.add_job(
                self.read_and_send,
                'interval',
                seconds=interval,
                args=[driver_name, driver_config],
                id=driver_name
            )

            logging.info(f"Scheduled: {driver_name} every {interval}s")

        # Start scheduler
        self.scheduler.start()
        logging.info("Runner started. Press Ctrl+C to stop.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Stopping runner...")
            self.scheduler.shutdown()
            logging.info("Runner stopped")


def main():
    print("=" * 60)
    print("Nettemp Client")
    print("Reading from: drivers_config.yaml")
    print("=" * 60)
    print()

    client = NettempClient(
        config_file='config.conf',
        drivers_config='drivers_config.yaml'
    )

    client.start()


if __name__ == "__main__":
    main()

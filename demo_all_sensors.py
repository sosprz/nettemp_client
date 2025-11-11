#!/usr/bin/env python3
"""
Demo script - Send fake data from all sensor drivers to cloud
Runs every 10 seconds with simulated sensor data
"""
import sys
import time
import random
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from nettemp import CloudClient, insert2
from driver_loader import DriverLoader

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


class FakeDriverRunner:
    """Run drivers with fake data when hardware is not available"""

    def __init__(self, config_file='test_config.conf'):
        self.loader = DriverLoader()
        self.cloud_client = CloudClient(config_file)
        self.iteration = 0

    def generate_fake_data(self, driver_name, config_dict):
        """Generate fake sensor data based on driver type"""

        # Try to run real driver first (for system, ping, etc.)
        real_data = self.loader.run_driver(driver_name, config_dict)
        if real_data:
            return real_data

        # Generate fake data if driver failed (no hardware)
        logging.info(f"Generating fake data for: {driver_name}")

        fake_generators = {
            'dht22': self._fake_dht22,
            'dht11': self._fake_dht11,
            'bme280': self._fake_bme280,
            'bmp180': self._fake_bmp180,
            'ds18b20': self._fake_ds18b20,
            'htu21d': self._fake_htu21d,
            'rpi': self._fake_rpi,
            'adxl343': self._fake_adxl343,
            'adxl345': self._fake_adxl345,
            'bh1750': self._fake_bh1750,
            'tsl2561': self._fake_tsl2561,
            'vl53l0x': self._fake_vl53l0x,
            'tmp102': self._fake_tmp102,
            'mpl3115a2': self._fake_mpl3115a2,
            'hih6130': self._fake_hih6130,
        }

        generator = fake_generators.get(driver_name)
        if generator:
            return generator(config_dict)

        return []

    def _fake_dht22(self, config):
        pin = config.get('gpio_pin', 4)
        temp = 20 + random.uniform(-2, 5) + (self.iteration * 0.1)
        humid = 60 + random.uniform(-5, 10)

        return [
            {"rom": f"_dht22_temp_gpio_D{pin}", "type": "temp", "value": round(temp, 1), "name": f"_dht22_temp_gpio_D{pin}"},
            {"rom": f"_dht22_humid_gpio_D{pin}", "type": "humid", "value": round(humid, 1), "name": f"_dht22_humid_gpio_D{pin}"}
        ]

    def _fake_dht11(self, config):
        pin = config.get('gpio_pin', 5)
        temp = 21 + random.uniform(-2, 4)
        humid = 58 + random.uniform(-5, 10)

        return [
            {"rom": f"_dht11_temp_gpio_D{pin}", "type": "temp", "value": round(temp, 1), "name": f"_dht11_temp_gpio_D{pin}"},
            {"rom": f"_dht11_humid_gpio_D{pin}", "type": "humid", "value": round(humid, 1), "name": f"_dht11_humid_gpio_D{pin}"}
        ]

    def _fake_bme280(self, config):
        addr = config.get('i2c_address', '0x76')
        temp = 22 + random.uniform(-2, 3)
        humid = 65 + random.uniform(-5, 8)
        press = 1013 + random.uniform(-10, 10)

        return [
            {"rom": "_i2c_76_temp", "type": "temp", "value": round(temp, 2), "name": "bme280_temp"},
            {"rom": "i2c_76_humid", "type": "humid", "value": round(humid, 2), "name": "bme280_humid"},
            {"rom": "_i2c_76_press", "type": "press", "value": round(press, 2), "name": "bme280_press"}
        ]

    def _fake_bmp180(self, config):
        temp = 21.5 + random.uniform(-1, 2)
        press = 1012 + random.uniform(-8, 8)

        return [
            {"rom": "_i2c_77_temp", "type": "temp", "value": round(temp, 2), "name": "bmp180_temp"},
            {"rom": "_i2c_77_press", "type": "press", "value": round(press, 2), "name": "bmp180_press"}
        ]

    def _fake_ds18b20(self, config):
        rom = config.get('rom', '28-00000a1b2c3d')
        temp = 19 + random.uniform(-1, 4)

        return [
            {"rom": rom, "type": "temp", "value": round(temp, 2), "name": "ds18b20"}
        ]

    def _fake_htu21d(self, config):
        temp = 23 + random.uniform(-2, 2)
        humid = 62 + random.uniform(-6, 6)

        return [
            {"rom": "_htu21d_temp", "type": "temp", "value": round(temp, 2), "name": "htu21d_temp"},
            {"rom": "_htu21d_humid", "type": "humid", "value": round(humid, 2), "name": "htu21d_humid"}
        ]

    def _fake_rpi(self, config):
        temp = 45 + random.uniform(-5, 15)
        return [
            {"rom": "_raspberrypi", "type": "temp", "value": round(temp, 1), "name": "raspberrypi"}
        ]

    def _fake_adxl343(self, config):
        return [
            {"rom": "_adxl343_x", "type": "accel", "value": round(random.uniform(-1, 1), 2), "name": "accel_x"},
            {"rom": "_adxl343_y", "type": "accel", "value": round(random.uniform(-1, 1), 2), "name": "accel_y"},
            {"rom": "_adxl343_z", "type": "accel", "value": round(random.uniform(9, 10), 2), "name": "accel_z"}
        ]

    def _fake_adxl345(self, config):
        return [
            {"rom": "_adxl345_x", "type": "accel", "value": round(random.uniform(-1, 1), 2), "name": "accel_x"},
            {"rom": "_adxl345_y", "type": "accel", "value": round(random.uniform(-1, 1), 2), "name": "accel_y"},
            {"rom": "_adxl345_z", "type": "accel", "value": round(random.uniform(9, 10), 2), "name": "accel_z"}
        ]

    def _fake_bh1750(self, config):
        light = 150 + random.uniform(-50, 100)
        return [
            {"rom": "_bh1750_light", "type": "light", "value": round(light, 1), "name": "bh1750"}
        ]

    def _fake_tsl2561(self, config):
        light = 200 + random.uniform(-80, 120)
        return [
            {"rom": "_tsl2561_light", "type": "light", "value": round(light, 1), "name": "tsl2561"}
        ]

    def _fake_vl53l0x(self, config):
        distance = 100 + random.uniform(-20, 50)
        return [
            {"rom": "_vl53l0x_distance", "type": "distance", "value": round(distance, 0), "name": "vl53l0x"}
        ]

    def _fake_tmp102(self, config):
        temp = 22.5 + random.uniform(-2, 3)
        return [
            {"rom": "_tmp102_temp", "type": "temp", "value": round(temp, 2), "name": "tmp102"}
        ]

    def _fake_mpl3115a2(self, config):
        temp = 21 + random.uniform(-1, 3)
        press = 1014 + random.uniform(-5, 5)
        alt = 120 + random.uniform(-2, 2)

        return [
            {"rom": "_mpl3115a2_temp", "type": "temp", "value": round(temp, 2), "name": "mpl3115a2_temp"},
            {"rom": "_mpl3115a2_press", "type": "press", "value": round(press, 2), "name": "mpl3115a2_press"},
            {"rom": "_mpl3115a2_alt", "type": "altitude", "value": round(alt, 1), "name": "mpl3115a2_alt"}
        ]

    def _fake_hih6130(self, config):
        temp = 22 + random.uniform(-2, 2)
        humid = 63 + random.uniform(-5, 5)

        return [
            {"rom": "_hih6130_temp", "type": "temp", "value": round(temp, 2), "name": "hih6130_temp"},
            {"rom": "_hih6130_humid", "type": "humid", "value": round(humid, 2), "name": "hih6130_humid"}
        ]

    def run_all_sensors(self):
        """Run all configured sensors and send data"""

        # Demo configuration for all sensor types
        demo_config = {
            "system": {"enabled": True, "read_in_sec": 10},
            "dht22": {"enabled": True, "read_in_sec": 10, "gpio_pin": 4},
            "dht11": {"enabled": True, "read_in_sec": 10, "gpio_pin": 5},
            "bme280": {"enabled": True, "read_in_sec": 10, "i2c_address": "0x76"},
            "bmp180": {"enabled": True, "read_in_sec": 10},
            "ds18b20": {"enabled": True, "read_in_sec": 10, "rom": "28-00000a1b2c3d"},
            "htu21d": {"enabled": True, "read_in_sec": 10},
            "rpi": {"enabled": True, "read_in_sec": 10},
            "adxl343": {"enabled": True, "read_in_sec": 10},
            "adxl345": {"enabled": True, "read_in_sec": 10},
            "bh1750": {"enabled": True, "read_in_sec": 10},
            "tsl2561": {"enabled": True, "read_in_sec": 10},
            "vl53l0x": {"enabled": True, "read_in_sec": 10},
            "tmp102": {"enabled": True, "read_in_sec": 10},
            "mpl3115a2": {"enabled": True, "read_in_sec": 10},
            "hih6130": {"enabled": True, "read_in_sec": 10},
            "ping": {"enabled": True, "read_in_sec": 10, "host": "8.8.8.8", "name": "google_dns"}
        }

        all_data = []

        for driver_name, config_dict in demo_config.items():
            if not config_dict.get('enabled'):
                continue

            readings = self.generate_fake_data(driver_name, config_dict)
            if readings:
                all_data.extend(readings)
                logging.info(f"✓ {driver_name}: {len(readings)} readings")

        # Send all data to cloud
        if all_data:
            logging.info(f"\n=== Sending {len(all_data)} readings to cloud ===")

            # Use insert2 for backward compatibility
            sender = insert2(all_data)
            sender.request()

            logging.info(f"=== Sent successfully ===\n")

        self.iteration += 1


def main():
    print("=" * 60)
    print("Nettemp Cloud - All Sensors Demo")
    print("Sending fake sensor data every 10 seconds")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    runner = FakeDriverRunner('test_config.conf')

    try:
        while True:
            runner.run_all_sensors()
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n\nStopped by user")
        logging.info("Demo stopped")


if __name__ == "__main__":
    main()

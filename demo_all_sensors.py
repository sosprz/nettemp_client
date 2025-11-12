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

    def __init__(self, config_file=None):
        """
        Initialize runner.

        Behavior changed: the demo will NOT fall back to `example_config.conf`.
        Use one of the following to point the demo at your production instance:
        - Pass an explicit config file path that exists: FakeDriverRunner('/path/to/config.conf')
        - Set environment variables: CLOUD_SERVER and CLOUD_API_KEY (the demo will
          create a temporary config and send to that server)

        If none of the above are provided the script will exit with an error to avoid
        accidentally sending to a non-production/example config.
        """

        import os
        import tempfile

        self.loader = DriverLoader()

        base = Path(__file__).parent
        chosen = None

        # 1) explicit config path provided and exists
        if config_file:
            cfg_path = Path(config_file)
            if cfg_path.is_file():
                # read only cloud_server and cloud_api_key from provided config
                try:
                    import yaml
                    parsed = yaml.safe_load(cfg_path.read_text()) or {}
                    cloud_server = parsed.get('cloud_server')
                    cloud_key = parsed.get('cloud_api_key')
                except Exception:
                    # fallback to simple grep-style parse
                    cloud_server = None
                    cloud_key = None
                    for line in cfg_path.read_text().splitlines():
                        if line.strip().startswith('cloud_server'):
                            cloud_server = line.split(':', 1)[1].strip()
                        if line.strip().startswith('cloud_api_key'):
                            cloud_key = line.split(':', 1)[1].strip()

                if cloud_server and cloud_key:
                    # create minimal temp config containing only server/key
                    import tempfile
                    tmp = tempfile.NamedTemporaryFile('w', delete=False, suffix='.yml')
                    tmp.write(f"group: demo\ncloud_server: {cloud_server}\ncloud_api_key: {cloud_key}\ncloud_enabled: true\n")
                    tmp.flush()
                    tmp.close()
                    chosen = tmp.name
                else:
                    print("Provided config file does not contain cloud_server/cloud_api_key")
                    sys.exit(1)
            else:
                print(f"Provided config file not found: {config_file}")
                sys.exit(1)

        # 2) environment variables for cloud server (preferred for quick prod testing)
        if not chosen:
            cloud_server = os.environ.get('CLOUD_SERVER')
            cloud_key = os.environ.get('CLOUD_API_KEY')
            if cloud_server and cloud_key:
                # write a small temporary YAML config that CloudClient can read
                tmp = tempfile.NamedTemporaryFile('w', delete=False, suffix='.yml')
                cfg = {
                    'group': os.environ.get('CLOUD_GROUP', 'demo'),
                    'cloud_server': cloud_server,
                    'cloud_api_key': cloud_key,
                    'cloud_enabled': True
                }
                try:
                    # write minimal YAML
                    tmp.write(f"group: {cfg['group']}\ncloud_server: {cfg['cloud_server']}\ncloud_api_key: {cfg['cloud_api_key']}\ncloud_enabled: true\n")
                    tmp.flush()
                    tmp.close()
                    chosen = tmp.name
                except Exception as e:
                    print(f"Failed to create temp config from env: {e}")
                    sys.exit(1)

        # 3) project config.conf (if present)
        if not chosen:
            candidate = base / 'config.conf'
            if candidate.is_file():
                # read only cloud_server and cloud_api_key from project config
                try:
                    import yaml
                    parsed = yaml.safe_load(candidate.read_text()) or {}
                    cloud_server = parsed.get('cloud_server')
                    cloud_key = parsed.get('cloud_api_key')
                except Exception:
                    cloud_server = None
                    cloud_key = None
                    for line in candidate.read_text().splitlines():
                        if line.strip().startswith('cloud_server'):
                            cloud_server = line.split(':', 1)[1].strip()
                        if line.strip().startswith('cloud_api_key'):
                            cloud_key = line.split(':', 1)[1].strip()

                if cloud_server and cloud_key:
                    import tempfile
                    tmp = tempfile.NamedTemporaryFile('w', delete=False, suffix='.yml')
                    tmp.write(f"group: demo\ncloud_server: {cloud_server}\ncloud_api_key: {cloud_key}\ncloud_enabled: true\n")
                    tmp.flush()
                    tmp.close()
                    chosen = tmp.name
                else:
                    # do not fall back to example
                    chosen = None

        # If we still don't have a config, fail rather than using example_config.conf
        if not chosen:
            print("No production config found. Provide a config file path or set CLOUD_SERVER and CLOUD_API_KEY environment variables.")
            sys.exit(1)

        logging.info(f"Using config file for demo: {chosen}")
        self.cloud_client = CloudClient(chosen)

        # Ensure demo runs under a predictable group/device id.
        # Prefer explicit CLOUD_GROUP env var, otherwise default to 'demo'.
        try:
            import os
            demo_group = os.environ.get('CLOUD_GROUP', 'demo')
            self.cloud_client.device_id = demo_group
            logging.info(f"Demo group set to: {self.cloud_client.device_id}")
        except Exception:
            # non-fatal: continue with whatever the CloudClient set
            pass
        self.iteration = 0

    def generate_fake_data(self, driver_name, config_dict):
        """Generate fake sensor data based on driver type"""
        # The demo should not attempt to use real hardware drivers.
        # Always generate synthetic readings so the demo can run on any machine.
        logging.info(f"Generating fake data for: {driver_name}")

        # Per-driver fake generators. If a specific fake generator is not
        # implemented for a driver, fall back to a generic synthetic reading
        # so every discovered driver yields at least one value.
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
            'system': self._fake_system,
        }

        generator = fake_generators.get(driver_name)
        if generator:
            return generator(config_dict)

        # Generic fallback: single numeric reading with a driver-prefixed ROM
        value = round(random.uniform(0, 100), 2)
        rom = f"_{driver_name}_value"
        return [{"rom": rom, "type": "generic", "value": value, "name": driver_name}]

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
        # BME280 commonly uses I2C address 0x76 (or 0x77). Use 0x76 for demo.
        temp = 22 + random.uniform(-2, 3)
        humid = 65 + random.uniform(-5, 8)
        press = 1013 + random.uniform(-10, 10)

        return [
            {"rom": "_i2c_76_temp", "type": "temp", "value": round(temp, 2), "name": "BME280-i2c-0x76"},
            {"rom": "_i2c_76_humid", "type": "humid", "value": round(humid, 2), "name": "BME280-i2c-0x76"},
            {"rom": "_i2c_76_press", "type": "press", "value": round(press, 2), "name": "BME280-i2c-0x76"}
        ]

    def _fake_bmp180(self, config):
        temp = 21.5 + random.uniform(-1, 2)
        press = 1012 + random.uniform(-8, 8)

        return [
            {"rom": "_i2c_77_temp", "type": "temp", "value": round(temp, 2), "name": "BMP180-i2c-0x77"},
            {"rom": "_i2c_77_press", "type": "press", "value": round(press, 2), "name": "BMP180-i2c-0x77"}
        ]

    def _fake_ds18b20(self, config):
        rom = config.get('rom', '28-00000a1b2c3d')
        temp = 19 + random.uniform(-1, 4)

        return [
            {"rom": rom, "type": "temp", "value": round(temp, 2), "name": "ds18b20"}
        ]

    def _fake_htu21d(self, config):
        # HTU21D default I2C address is 0x40
        temp = 23 + random.uniform(-2, 2)
        humid = 62 + random.uniform(-6, 6)

        return [
            {"rom": "_i2c_40_temp", "type": "temp", "value": round(temp, 2), "name": "HTU21D-i2c-0x40"},
            {"rom": "_i2c_40_humid", "type": "humid", "value": round(humid, 2), "name": "HTU21D-i2c-0x40"}
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
        # BH1750 default I2C address is 0x23
        light = 150 + random.uniform(-50, 100)
        return [
            {"rom": "_i2c_23_light", "type": "light", "value": round(light, 1), "name": "BH1750-i2c-0x23"}
        ]

    def _fake_tsl2561(self, config):
        # TSL2561 common I2C addresses include 0x39, 0x29, 0x49 — use 0x39 for demo
        light = 200 + random.uniform(-80, 120)
        return [
            {"rom": "_i2c_39_light", "type": "light", "value": round(light, 1), "name": "TSL2561-i2c-0x39"}
        ]

    def _fake_vl53l0x(self, config):
        # VL53L0X default I2C address is 0x29
        distance = 100 + random.uniform(-20, 50)
        return [
            {"rom": "_i2c_29_distance", "type": "distance", "value": round(distance, 0), "name": "VL53L0X-i2c-0x29"}
        ]

    def _fake_tmp102(self, config):
        # TMP102 default I2C address is 0x48
        temp = 22.5 + random.uniform(-2, 3)
        return [
            {"rom": "_i2c_48_temp", "type": "temp", "value": round(temp, 2), "name": "TMP102-i2c-0x48"}
        ]

    def _fake_mpl3115a2(self, config):
        # MPL3115A2 typical I2C address is 0x60
        temp = 21 + random.uniform(-1, 3)
        press = 1014 + random.uniform(-5, 5)
        alt = 120 + random.uniform(-2, 2)

        return [
            {"rom": "_i2c_60_temp", "type": "temp", "value": round(temp, 2), "name": "MPL3115A2-i2c-0x60"},
            {"rom": "_i2c_60_press", "type": "press", "value": round(press, 2), "name": "MPL3115A2-i2c-0x60"},
            {"rom": "_i2c_60_alt", "type": "altitude", "value": round(alt, 1), "name": "MPL3115A2-i2c-0x60"}
        ]

    def _fake_hih6130(self, config):
        # HIH6130 commonly appears at I2C address 0x27
        temp = 22 + random.uniform(-2, 2)
        humid = 63 + random.uniform(-5, 5)

        return [
            {"rom": "_i2c_27_temp", "type": "temp", "value": round(temp, 2), "name": "HIH6130-i2c-0x27"},
            {"rom": "_i2c_27_humid", "type": "humid", "value": round(humid, 2), "name": "HIH6130-i2c-0x27"}
        ]

    def _fake_system(self, config):
        # lightweight system-like metrics for demo purposes
        load = round(0.2 + random.random() * 1.8, 2)
        uptime = int(time.time()) % 100000
        return [
            {"rom": "_system_load", "type": "load", "value": load, "name": "system_load"},
            {"rom": "_system_uptime", "type": "uptime", "value": uptime, "name": "system_uptime"}
        ]

    def run_all_sensors(self):
        """Run all configured sensors and send data"""

        # Build a demo config enabling every discovered driver with sensible defaults
        discovered = self.loader.discover_drivers()
        demo_config = {name: {"enabled": True, "read_in_sec": 10} for name in discovered}

        all_data = []

        for driver_name, config_dict in demo_config.items():
            readings = self.generate_fake_data(driver_name, config_dict)
            if readings:
                all_data.extend(readings)
                logging.info(f"✓ {driver_name}: {len(readings)} readings")

        # Send all data to cloud
        if all_data:
            logging.info(f"\n=== Sending {len(all_data)} readings to cloud ===")

            # Use the CloudClient instance created with the demo's temporary config.
            # This ensures the demo uses the demo group (or CLOUD_GROUP) and the
            # temporary config we created instead of reading a local config.conf.
            try:
                if hasattr(self, 'cloud_client') and self.cloud_client:
                    self.cloud_client.send(all_data)
                    logging.info(f"=== Sent successfully (cloud client) ===\n")
                else:
                    # Fallback to backward-compatible insert2 if CloudClient not available
                    sender = insert2(all_data)
                    sender.request()
                    logging.info(f"=== Sent successfully (insert2 fallback) ===\n")
            except Exception as e:
                logging.error(f"Failed to send demo data: {e}")

        self.iteration += 1


def main():
    print("=" * 60)
    print("Nettemp Cloud - All Sensors Demo")
    print("Sending fake sensor data every 10 seconds")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    # Don't force a test config file; let FakeDriverRunner choose a sensible default
    runner = FakeDriverRunner()

    try:
        while True:
            runner.run_all_sensors()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n\nStopped by user")
        logging.info("Demo stopped")


if __name__ == "__main__":
    main()

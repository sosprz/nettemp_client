import sys
from types import ModuleType
from pathlib import Path

# Ensure `client` package root is on sys.path when tests run from inside `client/`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def setup_ads(voltage=2.1):
    # create fake modules and insert into sys.modules
    parent = ModuleType('adafruit_ads1x15')
    ads_mod = ModuleType('adafruit_ads1x15.ads1115')
    for i in range(4):
        setattr(ads_mod, f'P{i}', f'P{i}')

    class ADS1115:
        def __init__(self, i2c, address=0x48):
            self.address = address

    ads_mod.ADS1115 = ADS1115

    analog_mod = ModuleType('adafruit_ads1x15.analog_in')

    class AnalogIn:
        def __init__(self, ads, channel):
            self.voltage = analog_mod._voltage

    analog_mod.AnalogIn = AnalogIn
    analog_mod._voltage = voltage

    sys.modules['adafruit_ads1x15.ads1115'] = ads_mod
    sys.modules['adafruit_ads1x15.analog_in'] = analog_mod
    sys.modules['adafruit_ads1x15'] = parent


def import_driver():
    # Import driver after fakes are in place
    # Ensure a fresh import so module-level imports pick up our mocked adafruit modules
    import importlib
    sys.modules.pop('drivers.capacitive_soil', None)
    return importlib.import_module('drivers.capacitive_soil')


def test_capacitive_soil_wet():
    setup_ads(voltage=1.1)
    mod = import_driver()
    cfg = {'adc_channel': 0, 'i2c_address': '0x48', 'voltage_dry': 3.0, 'voltage_wet': 1.2}
    data = mod.capacitive_soil(cfg)
    assert any(d['type'] == 'moisture' for d in data)
    moist = float([d for d in data if d['type'] == 'moisture'][0]['value'])
    assert moist == 100.0


def test_capacitive_soil_dry():
    setup_ads(voltage=3.2)
    mod = import_driver()
    cfg = {'adc_channel': 0, 'i2c_address': '0x48', 'voltage_dry': 3.0, 'voltage_wet': 1.2}
    data = mod.capacitive_soil(cfg)
    moist = float([d for d in data if d['type'] == 'moisture'][0]['value'])
    assert moist == 0.0


def test_capacitive_soil_midpoint():
    mid = (1.2 + 3.0) / 2
    setup_ads(voltage=mid)
    mod = import_driver()
    cfg = {'adc_channel': 0, 'i2c_address': '0x48', 'voltage_dry': 3.0, 'voltage_wet': 1.2}
    data = mod.capacitive_soil(cfg)
    moist = float([d for d in data if d['type'] == 'moisture'][0]['value'])
    assert 45.0 <= moist <= 55.0

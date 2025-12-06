import sys
from types import ModuleType
from pathlib import Path

# Ensure `client` package root is on sys.path when tests run from inside `client/`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def setup_ads(voltage=2.5):
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


def test_ads1115_integration_reads_voltage():
    setup_ads(voltage=2.7)
    import importlib
    sys.modules.pop('drivers.capacitive_soil', None)
    capacitive_soil = importlib.import_module('drivers.capacitive_soil')
    cfg = {'adc_channel': 0, 'i2c_address': '0x48', 'voltage_dry': 3.0, 'voltage_wet': 1.2}
    data = capacitive_soil.capacitive_soil(cfg)
    # Ensure we have voltage reading present
    assert any(d['type'] == 'voltage' for d in data)
    volt = float([d for d in data if d['type'] == 'voltage'][0]['value'])
    assert abs(volt - 2.7) < 0.01

import sys
import time
from types import ModuleType
from pathlib import Path

# Ensure client root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def make_fake_digitalio(pulse_duration=0.005):
    """Create a fake digitalio module where setting the trigger pin high
    causes the echo pin to be high for `pulse_duration` seconds.
    """
    mod = ModuleType('digitalio')

    class Direction:
        OUT = 'out'
        IN = 'in'
        # aliases some drivers expect
        OUTPUT = 'out'
        INPUT = 'in'

    class DigitalInOut:
        # shared state across instances
        echo_pulse_end = 0.0

        def __init__(self, pin):
            self.pin = pin
            self.direction = None
            self._value = False

        @property
        def value(self):
            # If this is an input (echo), return True when within pulse window
            if self.direction == Direction.IN:
                return time.time() < DigitalInOut.echo_pulse_end
            return self._value

        @value.setter
        def value(self, v):
            # When trigger (output) goes high, set a future time for echo to be high
            if self.direction == Direction.OUT and v:
                DigitalInOut.echo_pulse_end = time.time() + pulse_duration
            self._value = bool(v)

        def deinit(self):
            pass

    mod.Direction = Direction
    mod.DigitalInOut = DigitalInOut
    return mod


def test_hcsr04_basic_distance():
    # Create and inject fake digitalio so driver picks it up on import
    fake_digitalio = make_fake_digitalio(pulse_duration=0.006)
    sys.modules['digitalio'] = fake_digitalio

    # board pins are provided by conftest; use pins 23/24 for trigger/echo
    import importlib
    # Ensure fresh import so module-level imports pick up our fake digitalio
    sys.modules.pop('drivers.hcsr04', None)
    hcsr04 = importlib.import_module('drivers.hcsr04')

    cfg = {'trigger_pin': 23, 'echo_pin': 24}
    data = hcsr04.hcsr04(cfg)

    assert isinstance(data, list)
    assert len(data) == 1
    rec = data[0]
    assert rec['type'] == 'distance'
    dist = float(rec['value'])
    # expected distance for pulse_duration=0.006s: (0.006*34300)/2 ~= 102.9 cm
    assert 90.0 <= dist <= 115.0

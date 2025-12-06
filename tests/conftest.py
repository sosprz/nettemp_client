import sys
from types import ModuleType


def fake_board():
    board = ModuleType('board')
    for i in range(40):
        setattr(board, f'D{i}', f'D{i}')
    # Provide common I2C pin names used by drivers
    board.SCL = 'SCL'
    board.SDA = 'SDA'
    return board


def fake_busio():
    busio = ModuleType('busio')

    class I2C:
        def __init__(self, scl, sda):
            pass

    busio.I2C = I2C
    return busio


def fake_digitalio():
    digitalio = ModuleType('digitalio')

    class Direction:
        OUT = 'out'
        IN = 'in'

    class DigitalInOut:
        def __init__(self, pin):
            self.pin = pin
            self.value = False
            self.direction = None

    digitalio.Direction = Direction
    digitalio.DigitalInOut = DigitalInOut
    return digitalio


def pytest_configure():
    # Provide no-op defaults so importing drivers during tests doesn't crash
    sys.modules.setdefault('board', fake_board())
    sys.modules.setdefault('busio', fake_busio())
    # adafruit modules will be inserted by individual tests when needed
    sys.modules.setdefault('digitalio', fake_digitalio())

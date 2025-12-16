import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Track last error time to avoid log spam
_last_error_time = 0
_error_interval = 300  # Only log errors every 5 minutes

def capacitive_soil(config_dict):
    """
    Capacitive Soil Moisture Sensor v1.2
    Reads analog voltage from ADC and converts to moisture percentage
    
    Requires: ADS1115 ADC connected via I2C
    
    Config:
        i2c_address: ADC I2C address (default 0x48)
        adc_channel: ADC channel number (0-3, default 0)
        voltage_dry: Voltage reading in dry air (calibration, default 3.0V)
        voltage_wet: Voltage reading in water (calibration, default 1.2V)
    """
    global _last_error_time, _error_interval
    
    try:
        # Get configuration
        i2c_address = config_dict.get("i2c_address", "0x48")
        if isinstance(i2c_address, str):
            i2c_address = int(i2c_address, 16)
        
        adc_channel = int(config_dict.get("adc_channel", 0))
        voltage_dry = float(config_dict.get("voltage_dry", 3.0))
        voltage_wet = float(config_dict.get("voltage_wet", 1.2))
        
        if not 0 <= adc_channel <= 3:
            print("Capacitive Soil: ADC channel must be 0-3")
            return []
        
        # Initialize I2C and ADC
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c, address=i2c_address)
        
        # Create analog input on specified channel
        channel = AnalogIn(ads, getattr(ADS, f'P{adc_channel}'))
        
        # Read voltage
        voltage = channel.voltage
        
        # Convert voltage to moisture percentage
        # Lower voltage = more moisture (capacitance increases)
        # Higher voltage = less moisture (capacitance decreases)
        if voltage >= voltage_dry:
            moisture = 0.0  # Dry
        elif voltage <= voltage_wet:
            moisture = 100.0  # Wet
        else:
            # Linear interpolation between dry and wet
            moisture = 100.0 - ((voltage - voltage_wet) / (voltage_dry - voltage_wet) * 100.0)
        
        # Clamp to 0-100%
        moisture = max(0.0, min(100.0, moisture))
        
        data = []
        
        # Moisture percentage reading
        moisture_value = '{0:0.1f}'.format(moisture)
        rom = f'_capacitive_soil_ch{adc_channel}_moist'
        data.append({
            "rom": rom,
            "type": "moisture",
            "value": moisture_value,
            "name": "soil_moisture",
            "unit": "%"
        })
        
        # Raw voltage reading (for debugging/calibration)
        voltage_value = '{0:0.3f}'.format(voltage)
        rom_volt = f'_capacitive_soil_ch{adc_channel}_volt'
        data.append({
            "rom": rom_volt,
            "type": "voltage",
            "value": voltage_value,
            "name": "soil_voltage",
            "unit": "V"
        })
        
        return data
        
    except Exception as e:
        current_time = time.time()
        error_msg = str(e)
        
        if "No I2C device at address" in error_msg or "I2C" in error_msg:
            if current_time - _last_error_time > _error_interval:
                print(f"Capacitive Soil: ADC not found at 0x{i2c_address:02x}. Check I2C connection.")
                print("  Install: pip3 install adafruit-circuitpython-ads1x15")
                _last_error_time = current_time
        elif "Permission denied" in error_msg:
            if current_time - _last_error_time > _error_interval:
                print("Capacitive Soil: I2C permission denied. Add user to i2c group:")
                print("  sudo usermod -a -G i2c $USER")
                print("  (then logout/login)")
                _last_error_time = current_time
        else:
            if current_time - _last_error_time > _error_interval:
                print(f"Capacitive Soil Error: {e}")
                _last_error_time = current_time
        return []

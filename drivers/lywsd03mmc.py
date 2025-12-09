import time
import adafruit_ble
from adafruit_ble.advertising.standard import Advertisement
from adafruit_ble_lywsd03mmc import LYWSD03MMCService

# Track BLE connection state
_ble = None
_connection = None
_last_error_time = 0
_error_interval = 300  # Only log errors every 5 minutes
_last_read_time = 0
_min_read_interval = 5  # Minimum 5 seconds between reads
_scan_timeout = 10  # Reduced scan timeout

def lywsd03mmc(config_dict):
    global _ble, _connection, _last_read_time, _last_error_time
    
    # Enforce minimum read interval
    current_time = time.time()
    time_since_last = current_time - _last_read_time
    if time_since_last < _min_read_interval and _last_read_time > 0:
        time.sleep(_min_read_interval - time_since_last)
    
    # Get device name from config (default to LYWSD03MMC)
    device_name = config_dict.get("device_name", "LYWSD03MMC")
    # Get MAC address if provided (optional, for faster connection)
    mac_address = config_dict.get("mac_address", None)
    # Get unique identifier for multiple sensors
    sensor_id = config_dict.get("sensor_id", "default")
    
    try:
        # Initialize BLE radio if needed
        if _ble is None:
            _ble = adafruit_ble.BLERadio()
        
        # Check if connection exists and is still valid
        if _connection is None or not _connection.connected:
            # Scan for device
            found = False
            for adv in _ble.start_scan(Advertisement, timeout=_scan_timeout):
                # Match by name or MAC address
                if adv.complete_name == device_name:
                    if mac_address is None or adv.address.string == mac_address:
                        _connection = _ble.connect(adv)
                        found = True
                        break
            
            _ble.stop_scan()
            
            if not found:
                error_time = time.time()
                if error_time - _last_error_time > _error_interval:
                    print(f"LYWSD03MMC: Device '{device_name}' not found")
                    _last_error_time = error_time
                return []
        
        # Read data from connected device
        if _connection and _connection.connected:
            service = _connection[LYWSD03MMCService]
            temp_humid = service.temperature_humidity
            
            if temp_humid and len(temp_humid) >= 2:
                temperature = temp_humid[0]
                humidity = temp_humid[1]
                
                _last_read_time = time.time()
                
                data = []
                
                # Temperature reading
                value = '{0:0.1f}'.format(temperature)
                rom = f'_lywsd03mmc_{sensor_id}_temp'
                type = 'temp'
                name = f'lywsd03mmc_temp'
                data.append({"rom": rom, "type": type, "value": value, "name": name})
                
                # Humidity reading
                value = '{0:0.1f}'.format(humidity)
                rom = f'_lywsd03mmc_{sensor_id}_humid'
                type = 'humid'
                name = f'lywsd03mmc_humid'
                data.append({"rom": rom, "type": type, "value": value, "name": name})
                
                return data
            else:
                error_time = time.time()
                if error_time - _last_error_time > _error_interval:
                    print(f"LYWSD03MMC: Invalid data received")
                    _last_error_time = error_time
                return []
        else:
            # Connection lost
            _connection = None
            return []
    
    except Exception as e:
        error_time = time.time()
        if error_time - _last_error_time > _error_interval:
            print(f"LYWSD03MMC Error: {e}")
            _last_error_time = error_time
        
        # Reset connection on error
        if _connection:
            try:
                _connection.disconnect()
            except:
                pass
            _connection = None
        
        return []

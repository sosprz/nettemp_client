import time

# BLE libraries are optional - only required if driver is enabled
try:
    import adafruit_ble
    from adafruit_ble.advertising.standard import Advertisement
    from adafruit_ble_lywsd03mmc import LYWSD03MMCService
    BLE_AVAILABLE = True
except ImportError as e:
    BLE_AVAILABLE = False
    _import_error = str(e)

# Track BLE connection state
_ble = None
_connections = {}  # Store connections by MAC address
_last_error_time = 0
_error_interval = 300  # Only log errors every 5 minutes
_last_read_time = 0
_min_read_interval = 5  # Minimum 5 seconds between reads
_scan_timeout = 20  # BLE scan timeout

def lywsd03mmc(config_dict):
    global _ble, _connections, _last_read_time, _last_error_time
    
    # Check if BLE libraries are available
    if not BLE_AVAILABLE:
        print(f"LYWSD03MMC: BLE libraries not available. Install with:")
        print(f"  pip3 install adafruit-circuitpython-ble adafruit-circuitpython-ble-lywsd03mmc")
        print(f"  Error: {_import_error}")
        return []
    
    # Enforce minimum read interval
    current_time = time.time()
    time_since_last = current_time - _last_read_time
    if time_since_last < _min_read_interval and _last_read_time > 0:
        time.sleep(_min_read_interval - time_since_last)
    
    # Get device name from config (default to LYWSD03MMC)
    device_name = "LYWSD03MMC"
    
    # Get MAC addresses (comma-separated list)
    mac_address_config = config_dict.get("mac_address", None)
    if not mac_address_config:
        return []
    
    # Parse comma-separated MAC addresses
    mac_addresses = [mac.strip() for mac in mac_address_config.split(',') if mac.strip()]
    
    all_data = []
    
    try:
        # Initialize BLE radio if needed
        if _ble is None:
            _ble = adafruit_ble.BLERadio()
        
        # Iterate through each MAC address
        for mac_address in mac_addresses:
            try:
                # Check if we have an existing connection for this MAC
                connection = _connections.get(mac_address)
                
                # If no connection or connection lost, establish new one
                if connection is None or not connection.connected:
                    found = False
                    
                    for adv in _ble.start_scan(Advertisement, timeout=_scan_timeout):
                        if adv.complete_name == device_name and adv.address.string == mac_address:
                            try:
                                connection = _ble.connect(adv)
                                _connections[mac_address] = connection
                                found = True
                                break
                            except Exception as e:
                                print(f"LYWSD03MMC: Failed to connect to {mac_address}: {e}")
                                connection = None
                                break
                    
                    _ble.stop_scan()
                    
                    if not found or not connection:
                        error_time = time.time()
                        if error_time - _last_error_time > _error_interval:
                            print(f"LYWSD03MMC: Device at {mac_address} not found")
                            _last_error_time = error_time
                        continue
                
                # Read data from connected device
                if connection and connection.connected:
                    service = connection[LYWSD03MMCService]
                    temp_humid = service.temperature_humidity
                    
                    if temp_humid and len(temp_humid) >= 2:
                        temperature = temp_humid[0]
                        humidity = temp_humid[1]
                        
                        _last_read_time = time.time()
                        
                        # Use MAC as device_id (remove colons, uppercase)
                        device_id = mac_address.replace(':', '').upper()
                        
                        # Temperature reading
                        value = '{0:0.1f}'.format(temperature)
                        rom = f'lywsd03mmc_{device_id}_temp'
                        type = 'temp'
                        name = f'lywsd03mmc_temp'
                        all_data.append({"rom": rom, "type": type, "value": value, "name": name, "device_id": device_id})
                        
                        # Humidity reading
                        value = '{0:0.1f}'.format(humidity)
                        rom = f'lywsd03mmc_{device_id}_humid'
                        type = 'humid'
                        name = f'lywsd03mmc_humid'
                        all_data.append({"rom": rom, "type": type, "value": value, "name": name, "device_id": device_id})
                
            except Exception as e:
                error_time = time.time()
                if error_time - _last_error_time > _error_interval:
                    print(f"LYWSD03MMC Error reading {mac_address}: {e}")
                    _last_error_time = error_time
                
                # Remove failed connection from cache
                if mac_address in _connections:
                    try:
                        _connections[mac_address].disconnect()
                    except:
                        pass
                    del _connections[mac_address]
        
        # Disconnect all connections after reading to save battery
        # They will reconnect on next read cycle
        for mac, conn in list(_connections.items()):
            try:
                if conn and conn.connected:
                    conn.disconnect()
            except Exception as e:
                print(f"LYWSD03MMC: Error disconnecting {mac}: {e}")
            finally:
                # Remove from cache so next read will create fresh connection
                if mac in _connections:
                    del _connections[mac]
    
    except Exception as e:
        error_time = time.time()
        if error_time - _last_error_time > _error_interval:
            print(f"LYWSD03MMC Error: {e}")
            _last_error_time = error_time
    
    return all_data

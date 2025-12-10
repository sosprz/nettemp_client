import time
import sys
import subprocess
import os

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
_connection_attempts = {}  # Track connection attempts per MAC
_last_error_time = 0
_error_interval = 300  # Only log errors every 5 minutes
_last_read_time = 0
_min_read_interval = 5  # Minimum 5 seconds between reads
_scan_timeout = 40  # BLE scan timeout (increased for stability)
_connection_timeout = 15  # Connection attempt timeout
_max_connection_attempts = 3  # Max retries before giving up
_connection_retry_interval = 60  # Wait 60s before retrying failed device
_immediate_retry_count = 2  # Immediate retries on connection failure
_last_bt_reset = 0  # Track last Bluetooth reset time
_bt_reset_interval = 300  # Reset Bluetooth every 5 minutes

def _reset_bluetooth():
    """Reset Bluetooth adapter to clear stale connections."""
    global _last_bt_reset
    
    current_time = time.time()
    if current_time - _last_bt_reset < _bt_reset_interval:
        return  # Don't reset too frequently
    
    try:
        print("LYWSD03MMC: Resetting Bluetooth adapter...", file=sys.stderr)
        
        # Try btmgmt first (preferred method)
        result = subprocess.run(['btmgmt', 'power', 'off'], 
                              capture_output=True, timeout=5)
        time.sleep(1)
        result = subprocess.run(['btmgmt', 'power', 'on'], 
                              capture_output=True, timeout=5)
        time.sleep(2)
        
        print("LYWSD03MMC: Bluetooth adapter reset complete", file=sys.stderr)
        _last_bt_reset = current_time
        
    except FileNotFoundError:
        # btmgmt not available, try hciconfig
        try:
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'down'], 
                         capture_output=True, timeout=5, check=False)
            time.sleep(1)
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'up'], 
                         capture_output=True, timeout=5, check=False)
            time.sleep(2)
            print("LYWSD03MMC: Bluetooth adapter reset complete (hciconfig)", file=sys.stderr)
            _last_bt_reset = current_time
        except Exception as e:
            print(f"LYWSD03MMC: Could not reset Bluetooth: {e}", file=sys.stderr)
            print(f"LYWSD03MMC: Add to sudoers: {os.getenv('USER')} ALL=(ALL) NOPASSWD: /usr/bin/btmgmt", file=sys.stderr)
            
    except subprocess.TimeoutExpired:
        print("LYWSD03MMC: Bluetooth reset timed out", file=sys.stderr)
    except Exception as e:
        print(f"LYWSD03MMC: Bluetooth reset error: {e}", file=sys.stderr)

def _should_retry_device(mac_address):
    """Check if we should retry connecting to a device that previously failed."""
    global _connection_attempts
    
    if mac_address not in _connection_attempts:
        return True
    
    attempts, last_attempt_time = _connection_attempts[mac_address]
    
    # If max attempts reached, check if enough time has passed to retry
    if attempts >= _max_connection_attempts:
        if time.time() - last_attempt_time >= _connection_retry_interval:
            # Reset attempts after cooldown period
            _connection_attempts[mac_address] = (0, time.time())
            return True
        return False
    
    return True


def _record_connection_attempt(mac_address, success):
    """Record a connection attempt for rate limiting."""
    global _connection_attempts
    
    if success:
        # Reset on success
        if mac_address in _connection_attempts:
            del _connection_attempts[mac_address]
    else:
        # Increment failure count
        attempts, _ = _connection_attempts.get(mac_address, (0, 0))
        _connection_attempts[mac_address] = (attempts + 1, time.time())


def lywsd03mmc(config_dict):
    global _ble, _connections, _last_read_time, _last_error_time
    
    # Check if BLE libraries are available
    if not BLE_AVAILABLE:
        print(f"LYWSD03MMC: BLE libraries not available. Install with:")
        print(f"  pip3 install adafruit-circuitpython-ble adafruit-circuitpython-ble-lywsd03mmc")
        print(f"  Error: {_import_error}")
        return []
    
    # Reset Bluetooth adapter periodically to clear stale connections
    _reset_bluetooth()
    
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
            # Skip devices that have failed too many times recently
            if not _should_retry_device(mac_address):
                continue
            
            connection = None
            read_success = False
            
            # Try up to _immediate_retry_count times for this device
            for retry in range(_immediate_retry_count):
                try:
                    # Check if we have an existing connection for this MAC
                    connection = _connections.get(mac_address)
                
                    # If no connection or connection lost, establish new one
                    if connection is None or not connection.connected:
                        found = False
                        
                        if retry > 0:
                            print(f"LYWSD03MMC: Retry {retry}/{_immediate_retry_count-1} for {mac_address}", file=sys.stderr)
                            time.sleep(2)  # Brief wait before retry
                        
                        # Scan with timeout
                        scan_start = time.time()
                        for adv in _ble.start_scan(Advertisement, timeout=_scan_timeout):
                            # Check for early timeout (more responsive)
                            if time.time() - scan_start > _scan_timeout:
                                break
                            
                            if adv.complete_name == device_name and adv.address.string == mac_address:
                                try:
                                    print(f"LYWSD03MMC: Attempting connection to {mac_address}...", file=sys.stderr)
                                    connection = _ble.connect(adv, timeout=_connection_timeout)
                                    
                                    # Verify connection is active
                                    if not connection or not connection.connected:
                                        print(f"LYWSD03MMC: Connection to {mac_address} failed (not connected)", file=sys.stderr)
                                        connection = None
                                        break
                                    
                                    _connections[mac_address] = connection
                                    found = True
                                    print(f"LYWSD03MMC: Connected to {mac_address}", file=sys.stderr)
                                    
                                    # Wait for connection to stabilize before reading
                                    time.sleep(3)
                                    break
                                except Exception as e:
                                    print(f"LYWSD03MMC: Failed to connect to {mac_address}: {e}", file=sys.stderr)
                                    connection = None
                                    break
                        
                        _ble.stop_scan()
                        
                        if not found or not connection:
                            if retry == _immediate_retry_count - 1:
                                # Last retry failed
                                _record_connection_attempt(mac_address, False)
                                error_time = time.time()
                                if error_time - _last_error_time > _error_interval:
                                    print(f"LYWSD03MMC: Device at {mac_address} not found after {_immediate_retry_count} attempts", file=sys.stderr)
                                    _last_error_time = error_time
                            continue                    # Read data from connected device
                    if connection and connection.connected:
                        # Additional delay before reading for stability
                        time.sleep(2)
                        
                        print(f"LYWSD03MMC: Reading data from {mac_address}...", file=sys.stderr)
                        
                        try:
                            service = connection[LYWSD03MMCService]
                            print(f"LYWSD03MMC: Got service from {mac_address}", file=sys.stderr)
                            
                            # Try reading up to 3 times with delays
                            temp_humid = None
                            for read_attempt in range(3):
                                temp_humid = service.temperature_humidity
                                
                                if temp_humid and len(temp_humid) >= 2:
                                    # Valid data received
                                    break
                                else:
                                    # Data not ready, wait and retry
                                    if read_attempt < 2:
                                        print(f"LYWSD03MMC: Data not ready from {mac_address}, retrying ({read_attempt+1}/3)...", file=sys.stderr)
                                        time.sleep(2)
                            
                            print(f"LYWSD03MMC: Raw data from {mac_address}: {temp_humid}", file=sys.stderr)
                            
                            if temp_humid and len(temp_humid) >= 2:
                                temperature = temp_humid[0]
                                humidity = temp_humid[1]
                                
                                _last_read_time = time.time()
                                
                                # Use MAC as device_id (remove colons, uppercase)
                                device_id = mac_address.replace(':', '').upper()
                                
                                # Temperature reading (use device_id in name for uniqueness)
                                temp_value = '{0:0.1f}'.format(temperature)
                                temp_rom = f'lywsd03mmc_{device_id}_temp'
                                temp_reading = {"rom": temp_rom, "type": "temp", "value": temp_value, "name": f"lywsd03mmc_{device_id}_temp", "device_id": device_id}
                                all_data.append(temp_reading)
                                print(f"LYWSD03MMC: Added temp reading: {temp_reading}", file=sys.stderr)
                                
                                # Humidity reading (use device_id in name for uniqueness)
                                humid_value = '{0:0.1f}'.format(humidity)
                                humid_rom = f'lywsd03mmc_{device_id}_humid'
                                humid_reading = {"rom": humid_rom, "type": "humid", "value": humid_value, "name": f"lywsd03mmc_{device_id}_humid", "device_id": device_id}
                                all_data.append(humid_reading)
                                print(f"LYWSD03MMC: Added humid reading: {humid_reading}", file=sys.stderr)
                                
                                print(f"LYWSD03MMC: Read {mac_address} - Temp: {temperature}°C, Humid: {humidity}%", file=sys.stderr)
                                _record_connection_attempt(mac_address, True)
                                read_success = True
                                break  # Success, exit retry loop
                            else:
                                print(f"LYWSD03MMC: No valid data from {mac_address} after 3 read attempts", file=sys.stderr)
                        
                        except Exception as read_error:
                            print(f"LYWSD03MMC: Error reading service from {mac_address}: {read_error}", file=sys.stderr)
                            import traceback
                            traceback.print_exc()
                
                except Exception as e:
                    error_time = time.time()
                    if error_time - _last_error_time > _error_interval:
                        print(f"LYWSD03MMC Error reading {mac_address}: {e}", file=sys.stderr)
                        _last_error_time = error_time
                    
                    # Remove failed connection from cache
                    if mac_address in _connections:
                        try:
                            _connections[mac_address].disconnect()
                        except:
                            pass
                        del _connections[mac_address]
                    
                    # Don't break retry loop on error, try again
                    if retry < _immediate_retry_count - 1:
                        continue
        
        # Disconnect all connections after reading to save battery
        # They will reconnect on next read cycle
        for mac, conn in list(_connections.items()):
            try:
                if conn and conn.connected:
                    conn.disconnect()
                    print(f"LYWSD03MMC: Disconnected {mac}", file=sys.stderr)
            except Exception as e:
                print(f"LYWSD03MMC: Error disconnecting {mac}: {e}", file=sys.stderr)
            finally:
                # Remove from cache so next read will create fresh connection
                if mac in _connections:
                    del _connections[mac]
    
    except KeyboardInterrupt:
        # Clean shutdown on Ctrl+C
        print("LYWSD03MMC: Shutting down...", file=sys.stderr)
        for mac, conn in list(_connections.items()):
            try:
                if conn and conn.connected:
                    conn.disconnect()
            except:
                pass
        _connections.clear()
        raise
    
    except Exception as e:
        error_time = time.time()
        if error_time - _last_error_time > _error_interval:
            print(f"LYWSD03MMC Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            _last_error_time = error_time
        
        # Clean up connections on error
        for mac in list(_connections.keys()):
            try:
                conn = _connections[mac]
                if conn and conn.connected:
                    conn.disconnect()
            except:
                pass
            del _connections[mac]
    
    return all_data

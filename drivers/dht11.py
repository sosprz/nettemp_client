import time, socket
import board
import adafruit_dht

# Track last error time to avoid log spam
_last_error_time = 0
_error_interval = 300  # Only log errors every 5 minutes
_last_read_time = 0
_min_read_interval = 1.5  # DHT11 needs minimum 1 second between reads
_dht_device = None  # Reuse same device instance
_current_pin = None

def dht11(config_dict):
  global _last_read_time, _dht_device, _current_pin
  
  # Enforce minimum read interval - DHT11 needs cooldown
  current_time = time.time()
  time_since_last = current_time - _last_read_time
  if time_since_last < _min_read_interval and _last_read_time > 0:
    time.sleep(_min_read_interval - time_since_last)
  
  pin = str(config_dict.get("gpio_pin"))
  pin = "D"+pin
  
  try:
    # Reuse existing device if pin hasn't changed
    if _dht_device is None or _current_pin != pin:
      # Clean up old device if exists
      if _dht_device is not None:
        try:
          _dht_device.exit()
        except:
          pass
      # Create new device
      _dht_device = adafruit_dht.DHT11(getattr(board,pin), use_pulseio=False)
      _current_pin = pin
    
    dht_device = _dht_device
    
    # DHT sensors are unreliable, retry up to 3 times
    temperature = None
    humidity = None
    max_retries = 3
    
    for attempt in range(max_retries):
      try:
        temperature = dht_device.temperature
        humidity = dht_device.humidity
        if temperature is not None and humidity is not None:
          _last_read_time = time.time()  # Update last read time on success
          break
      except RuntimeError as e:
        # Common DHT errors: checksum, timeout, not found
        _last_read_time = time.time()  # Update even on failure to track attempts
        if attempt < max_retries - 1:
          time.sleep(2)  # Wait before retry
        else:
          # Only log errors periodically to avoid spam
          global _last_error_time
          error_time = time.time()
          if error_time - _last_error_time > _error_interval:
            print(f"DHT11: Failed after {max_retries} attempts: {e}")
            _last_error_time = error_time
    
    data = []
    if humidity is not None and temperature is not None:
      # Extract just the GPIO number (remove 'D' prefix)
      gpio_num = pin[1:] if pin.startswith('D') else pin
      
      value = '{0:0.1f}'.format(temperature)
      rom = f'_dht11_gpio{gpio_num}_temp'
      type = 'temp'
      name = f'dht11_temp'
      data.append({"rom":rom,"type":type, "value":value,"name":name})
    
      value = '{0:0.1f}'.format(humidity)
      rom = f'_dht11_gpio{gpio_num}_humid'
      type = 'humid'
      name = f'dht11_humid'
      data.append({"rom":rom,"type":type, "value":value,"name":name})

    return data

  except Exception as e:
    error_msg = str(e)
    if "Unable to set line" in error_msg or "Permission denied" in error_msg:
      print(f"DHT11: GPIO permission denied. Run with sudo or add user to gpio group:")
      print(f"  sudo usermod -a -G gpio $USER")
      print(f"  (then logout/login)")
    else:
      print(f"DHT11 Error: {e}")
    return []
  # Don't call exit() - keep device alive for next read
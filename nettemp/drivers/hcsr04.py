import time
import board
import digitalio

# Track last error time to avoid log spam
_last_error_time = 0
_error_interval = 300  # Only log errors every 5 minutes

def hcsr04(config_dict):
    """
    HC-SR04 Ultrasonic Distance Sensor
    Measures distance in centimeters
    
    Config:
        trigger_pin: GPIO pin number for TRIG
        echo_pin: GPIO pin number for ECHO
    """
    global _last_error_time, _error_interval
    
    try:
        trigger_pin = config_dict.get("trigger_pin")
        echo_pin = config_dict.get("echo_pin")
        
        if not trigger_pin or not echo_pin:
            print("HC-SR04: Missing trigger_pin or echo_pin in config")
            return []
        
        # Setup GPIO pins
        trigger_pin_name = f"D{trigger_pin}"
        echo_pin_name = f"D{echo_pin}"
        
        trig = digitalio.DigitalInOut(getattr(board, trigger_pin_name))
        echo = digitalio.DigitalInOut(getattr(board, echo_pin_name))
        
        trig.direction = digitalio.Direction.OUTPUT
        echo.direction = digitalio.Direction.INPUT
        
        # Ensure trigger is low
        trig.value = False
        time.sleep(0.1)
        
        # Send 10us pulse to trigger
        trig.value = True
        time.sleep(0.00001)  # 10 microseconds
        trig.value = False
        
        # Wait for echo to go high (start of pulse)
        pulse_start = time.time()
        timeout = time.time() + 0.1  # 100ms timeout
        while echo.value == False:
            pulse_start = time.time()
            if pulse_start > timeout:
                raise TimeoutError("Echo pin timeout (start)")
        
        # Wait for echo to go low (end of pulse)
        pulse_end = time.time()
        timeout = time.time() + 0.1  # 100ms timeout
        while echo.value == True:
            pulse_end = time.time()
            if pulse_end > timeout:
                raise TimeoutError("Echo pin timeout (end)")
        
        # Calculate distance
        pulse_duration = pulse_end - pulse_start
        # Speed of sound = 34300 cm/s
        # Distance = (Time × Speed) / 2 (round trip)
        distance = (pulse_duration * 34300) / 2
        
        # Cleanup
        trig.deinit()
        echo.deinit()
        
        # HC-SR04 range: 2cm to 400cm
        if distance < 2 or distance > 400:
            print(f"HC-SR04: Distance out of range: {distance:.1f}cm")
            return []
        
        data = []
        value = '{0:0.1f}'.format(distance)
        rom = f'_hcsr04_gpio{trigger_pin}_{echo_pin}_dist'
        type = 'distance'
        name = 'hcsr04_distance'
        data.append({"rom": rom, "type": type, "value": value, "name": name, "unit": "cm"})
        
        return data
        
    except TimeoutError as e:
        # Sensor not responding or no object detected
        current_time = time.time()
        if current_time - _last_error_time > _error_interval:
            print(f"HC-SR04: {e}")
            _last_error_time = current_time
        return []
    except Exception as e:
        current_time = time.time()
        error_msg = str(e)
        if "Permission denied" in error_msg:
            if current_time - _last_error_time > _error_interval:
                print("HC-SR04: GPIO permission denied. Run with sudo or add user to gpio group:")
                print("  sudo usermod -a -G gpio $USER")
                print("  (then logout/login)")
                _last_error_time = current_time
        else:
            if current_time - _last_error_time > _error_interval:
                print(f"HC-SR04 Error: {e}")
                _last_error_time = current_time
        return []

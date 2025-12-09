#!/usr/bin/env python3
"""
Test script for LYWSD03MMC Xiaomi BLE sensor driver
Run this to verify the sensor is working before adding to nettemp
"""

import sys
import time

# Add drivers to path
sys.path.insert(0, '.')

try:
    from drivers.lywsd03mmc import lywsd03mmc
except ImportError as e:
    print(f"Error importing driver: {e}")
    print("Make sure you have installed the required libraries:")
    print("  pip3 install adafruit-circuitpython-ble")
    print("  pip3 install adafruit-circuitpython-ble-lywsd03mmc")
    sys.exit(1)

def test_sensor():
    """Test the LYWSD03MMC sensor"""
    print("="*60)
    print("Xiaomi LYWSD03MMC BLE Sensor Test")
    print("="*60)
    print("\nScanning for LYWSD03MMC sensors...")
    print("Make sure your sensor is nearby and has a fresh battery.\n")
    
    # Test configuration
    config = {
        "device_name": "LYWSD03MMC",
        "mac_address": None,  # Set to specific MAC if you have multiple sensors
        "sensor_id": "test"
    }
    
    print(f"Configuration:")
    print(f"  Device Name: {config['device_name']}")
    print(f"  MAC Address: {config['mac_address'] or 'Any (first found)'}")
    print(f"  Sensor ID: {config['sensor_id']}")
    print()
    
    # Try to read data
    print("Attempting to read sensor data...")
    print("This may take 10-20 seconds on first connection...\n")
    
    for attempt in range(3):
        print(f"Attempt {attempt + 1}/3...")
        data = lywsd03mmc(config)
        
        if data:
            print("\n✓ SUCCESS! Sensor data received:")
            print("-" * 60)
            for reading in data:
                print(f"  ROM: {reading['rom']}")
                print(f"  Type: {reading['type']}")
                print(f"  Value: {reading['value']}")
                print(f"  Name: {reading['name']}")
                print()
            print("-" * 60)
            print("\n✓ Driver is working correctly!")
            print("\nYou can now enable it in drivers_config.yaml:")
            print("  lywsd03mmc:")
            print("    enabled: true")
            print("    read_in_sec: 300")
            print("    device_name: 'LYWSD03MMC'")
            return True
        else:
            print(f"  No data received (attempt {attempt + 1}/3)")
            if attempt < 2:
                print("  Waiting 5 seconds before retry...")
                time.sleep(5)
    
    print("\n✗ Failed to read sensor data")
    print("\nTroubleshooting:")
    print("1. Check that Bluetooth is enabled:")
    print("   sudo systemctl status bluetooth")
    print("\n2. Scan for BLE devices:")
    print("   sudo hcitool lescan")
    print("\n3. Verify sensor is powered and nearby (< 10m)")
    print("\n4. Try running with sudo:")
    print("   sudo python3 test_lywsd03mmc.py")
    print("\n5. Check battery level in sensor")
    return False

if __name__ == "__main__":
    try:
        success = test_sensor()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

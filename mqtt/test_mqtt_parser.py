#!/usr/bin/env python3
"""
Test MQTT parser with example messages
"""

import sys
import json
from mqtt.mqtt_parsers import MQTTParser

def test_theengs():
    """Test Theengs Gateway message parsing"""
    print("=" * 80)
    print("Testing Theengs Gateway Parser")
    print("=" * 80)
    
    parser = MQTTParser()
    
    topic = "home/TheengsGateway/BTtoMQTT/A4C138165B5D"
    payload = json.dumps({
        "name": "ATC_165B5D",
        "id": "A4:C1:38:16:5B:5D",
        "rssi": -71,
        "brand": "Xiaomi",
        "model": "TH Sensor",
        "model_id": "LYWSD03MMC/MJWSD05MMC_ATC",
        "type": "THB",
        "tempc": 20.5,
        "tempf": 68.9,
        "hum": 57,
        "batt": 88,
        "volt": 2.909,
        "mac": "A4:C1:38:16:5B:5D"
    })
    
    print(f"\nTopic: {topic}")
    print(f"Payload: {payload}")
    print("\nParsing...")
    
    readings = parser.parse(topic, payload)
    
    if readings:
        print(f"\n✅ Successfully parsed {len(readings)} reading(s):")
        print("-" * 80)
        for i, reading in enumerate(readings, 1):
            print(f"\nReading #{i}:")
            print(f"  Device ID:     {reading['device_id']}")
            print(f"  Sensor ID:     {reading['sensor_id']}")
            print(f"  Sensor Type:   {reading['sensor_type']}")
            print(f"  Value:         {reading['value']} {reading['unit']}")
            print(f"  Friendly Name: {reading['friendly_name']}")
    else:
        print("\n❌ Failed to parse message")
        return False
    
    return True

def test_espeasy():
    """Test ESPEasy message parsing"""
    print("\n" + "=" * 80)
    print("Testing ESPEasy Parser")
    print("=" * 80)
    
    parser = MQTTParser()
    
    topic = "ESPEasyMega_1/bme280/temperature"
    payload = "22.5"
    
    print(f"\nTopic: {topic}")
    print(f"Payload: {payload}")
    print("\nParsing...")
    
    readings = parser.parse(topic, payload)
    
    if readings:
        print(f"\n✅ Successfully parsed {len(readings)} reading(s):")
        print("-" * 80)
        for i, reading in enumerate(readings, 1):
            print(f"\nReading #{i}:")
            print(f"  Device ID:     {reading['device_id']}")
            print(f"  Sensor ID:     {reading['sensor_id']}")
            print(f"  Sensor Type:   {reading['sensor_type']}")
            print(f"  Value:         {reading['value']}")
            print(f"  Friendly Name: {reading['friendly_name']}")
    else:
        print("\n❌ Failed to parse message")
        return False
    
    return True

def test_zigbee2mqtt():
    """Test Zigbee2MQTT message parsing"""
    print("\n" + "=" * 80)
    print("Testing Zigbee2MQTT Parser")
    print("=" * 80)
    
    parser = MQTTParser()
    
    topic = "zigbee2mqtt/living_room_sensor"
    payload = json.dumps({
        "temperature": 22.5,
        "humidity": 45,
        "battery": 100,
        "linkquality": 120
    })
    
    print(f"\nTopic: {topic}")
    print(f"Payload: {payload}")
    print("\nParsing...")
    
    readings = parser.parse(topic, payload)
    
    if readings:
        print(f"\n✅ Successfully parsed {len(readings)} reading(s):")
        print("-" * 80)
        for i, reading in enumerate(readings, 1):
            print(f"\nReading #{i}:")
            print(f"  Device ID:     {reading['device_id']}")
            print(f"  Sensor ID:     {reading['sensor_id']}")
            print(f"  Sensor Type:   {reading['sensor_type']}")
            print(f"  Value:         {reading['value']} {reading['unit']}")
            print(f"  Friendly Name: {reading['friendly_name']}")
    else:
        print("\n❌ Failed to parse message")
        return False
    
    return True

if __name__ == '__main__':
    print("\n🧪 MQTT Parser Tests\n")
    
    results = []
    results.append(("Theengs Gateway", test_theengs()))
    results.append(("ESPEasy", test_espeasy()))
    results.append(("Zigbee2MQTT", test_zigbee2mqtt()))
    
    print("\n" + "=" * 80)
    print("Test Results Summary")
    print("=" * 80)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name:20s} {status}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)

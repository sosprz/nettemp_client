#!/usr/bin/env python3
"""
Quick test for MQTT Bridge functionality
Run this to verify MQTT setup without starting the full client
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mqtt import MQTTBridge

def test_mqtt_connection():
    """Test basic MQTT connection"""
    print("╔════════════════════════════════════════════════════════╗")
    print("║     Nettemp MQTT Bridge - Connection Test             ║")
    print("╚════════════════════════════════════════════════════════╝")
    print()
    
    # Test config
    config = {
        'enabled': True,
        'mode': 'publisher',
        'broker': 'localhost',
        'port': 1883,
        'topic_prefix': 'nettemp/test',
        'qos': 0,
        'retain': False
    }
    
    print("Test Configuration:")
    print(f"  Broker: {config['broker']}:{config['port']}")
    print(f"  Mode: {config['mode']}")
    print(f"  Topic Prefix: {config['topic_prefix']}")
    print()
    
    # Create mock cloud client
    class MockCloudClient:
        def __init__(self):
            self.device_id = 'test-device'
    
    cloud_client = MockCloudClient()
    
    # Create MQTT bridge
    print("Initializing MQTT bridge...")
    mqtt = MQTTBridge(cloud_client, 'test-device', config)
    
    if not mqtt.enabled:
        print("❌ MQTT not enabled (check if paho-mqtt is installed)")
        print("   Run: pip install paho-mqtt")
        return False
    
    print("✅ MQTT bridge initialized")
    print()
    
    # Start connection
    print("Connecting to MQTT broker...")
    mqtt.start()
    
    # Wait for connection
    max_wait = 5
    waited = 0
    while not mqtt.is_connected() and waited < max_wait:
        time.sleep(0.5)
        waited += 0.5
    
    if not mqtt.is_connected():
        print(f"❌ Failed to connect to {config['broker']}:{config['port']}")
        print()
        print("Troubleshooting:")
        print("  1. Check if MQTT broker is running")
        print("     - For local Mosquitto: sudo systemctl status mosquitto")
        print("     - Or install: sudo apt-get install mosquitto")
        print("  2. Check firewall rules")
        print("  3. Verify broker hostname and port")
        mqtt.stop()
        return False
    
    print(f"✅ Connected to {config['broker']}:{config['port']}")
    print()
    
    # Test publishing
    print("Testing message publishing...")
    test_readings = [
        {
            'rom': 'test_sensor_1',
            'type': 'temperature',
            'value': 22.5,
            'unit': '°C',
            'name': 'Test Sensor/temperature'
        },
        {
            'rom': 'test_sensor_2',
            'type': 'humidity',
            'value': 65,
            'unit': '%',
            'name': 'Test Sensor/humidity'
        }
    ]
    
    success = mqtt.publish_readings(test_readings, 'test-device')
    
    if success:
        print("✅ Test messages published successfully")
        print()
        print("Published to topics:")
        for reading in test_readings:
            topic = f"{config['topic_prefix']}/test-device/{reading['rom']}/{reading['type']}"
            print(f"  - {topic}")
        print()
        print("To verify, run in another terminal:")
        print(f"  mosquitto_sub -h {config['broker']} -t \"{config['topic_prefix']}/#\" -v")
    else:
        print("⚠️  Failed to publish messages")
        print("   Check MQTT broker logs for errors")
    
    print()
    
    # Cleanup
    print("Disconnecting...")
    mqtt.stop()
    time.sleep(1)
    
    print("✅ Test completed")
    return success

def test_subscriber_mode():
    """Test subscriber mode (requires manual message publishing)"""
    print()
    print("╔════════════════════════════════════════════════════════╗")
    print("║     Subscriber Mode Test (Manual)                     ║")
    print("╚════════════════════════════════════════════════════════╝")
    print()
    print("This test will listen for MQTT messages for 30 seconds")
    print()
    
    config = {
        'enabled': True,
        'mode': 'subscriber',
        'broker': 'localhost',
        'port': 1883,
        'subscribe_topics': ['nettemp/test/#', 'sensors/#']
    }
    
    print("Test Configuration:")
    print(f"  Broker: {config['broker']}:{config['port']}")
    print(f"  Topics: {', '.join(config['subscribe_topics'])}")
    print()
    
    # Mock cloud client
    class MockCloudClient:
        def __init__(self):
            self.device_id = 'test-device'
            self.received_count = 0
        
        def send_payload(self, payload):
            self.received_count += 1
            print(f"✅ Received and forwarded message #{self.received_count}:")
            print(f"   {payload}")
            return True
    
    cloud_client = MockCloudClient()
    
    # Create MQTT bridge
    mqtt = MQTTBridge(cloud_client, 'test-device', config)
    
    if not mqtt.enabled:
        print("❌ MQTT not available")
        return False
    
    mqtt.start()
    
    # Wait for connection
    time.sleep(2)
    
    if not mqtt.is_connected():
        print(f"❌ Failed to connect to {config['broker']}:{config['port']}")
        return False
    
    print(f"✅ Connected and subscribed to topics")
    print()
    print("Listening for messages...")
    print()
    print("Publish a test message with:")
    print(f"  mosquitto_pub -h {config['broker']} -t \"sensors/test\" \\")
    print('    -m \'{"rom":"test","type":"temperature","value":25}\'')
    print()
    print("Waiting 30 seconds...")
    
    # Wait for messages
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    print()
    print(f"Received {cloud_client.received_count} message(s)")
    
    mqtt.stop()
    
    return True

if __name__ == '__main__':
    print()
    
    # Test 1: Connection and Publishing
    success = test_mqtt_connection()
    
    if success:
        print()
        response = input("Run subscriber test? (y/n): ").strip().lower()
        if response == 'y':
            test_subscriber_mode()
    
    print()
    print()

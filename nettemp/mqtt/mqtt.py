"""
MQTT Bridge for Nettemp Client

Two operation modes:
1. Publisher: Send sensor readings to remote MQTT broker
2. Subscriber: Receive MQTT messages and forward to cloud servers (like HTTP bridge)

Configuration in config.conf:
    mqtt:
      enabled: true
      mode: both              # publisher, subscriber, or both
      broker: mqtt.example.com
      port: 1883
      username: user          # optional
      password: pass          # optional
      tls: false              # use TLS/SSL
      
      # Topic logging (optional):
      # This helps `nettemp config` autodiscovery by recording seen topics to mqtt_topics.log.
      # Subscriptions here are ONLY for logging; they do not enable MQTT→Cloud forwarding.
      # Recommended (BLE gateways): home/+/BTtoMQTT/+
      topic_log_subscribe_topics:
        - home/+/BTtoMQTT/+
       
      # Publisher settings
      topic_prefix: nettemp   # default: nettemp/{group}/{sensor_id}/{type}
      qos: 0                  # 0, 1, or 2
      retain: false
      
      # Subscriber settings
      subscribe_topics:       # topics to listen to
        - sensors/#
        - home/+/temperature
      auth_token: shared_secret  # optional - validates incoming messages
"""

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Optional, Any

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    mqtt = None

from ..nettemp import insert2
from ..paths import get_data_dir, get_mqtt_topic_log_file
from .mqtt_parsers import MQTTParser


class MQTTBridge:
    """MQTT bridge that can publish sensor data and/or receive MQTT messages to forward to cloud"""

    def __init__(self, cloud_client, default_device_id: str, config: dict | None):
        self.cloud_client = cloud_client
        self.default_device_id = default_device_id or 'nettemp-client'
        
        if not MQTT_AVAILABLE:
            logging.warning('MQTT support not available - install paho-mqtt: pip install paho-mqtt')
            self.enabled = False
            return
        
        cfg = config or {}
        self.enabled = bool(cfg.get('enabled', False))
        
        if not self.enabled:
            return
        
        # Connection settings
        self.broker = cfg.get('broker', '')
        self.port = int(cfg.get('port', 1883))
        self.username = cfg.get('username')
        self.password = cfg.get('password')
        self.use_tls = bool(cfg.get('tls', False))
        self.keepalive = int(cfg.get('keepalive', 60))
        # 0.0.0.0 is a bind/listen address, not a client connect address.
        if self.broker == '0.0.0.0':
            self.broker = '127.0.0.1'
        
        # Operation mode
        mode = cfg.get('mode', 'both').lower()
        self.mode_publisher = mode in ['publisher', 'both']
        self.mode_subscriber = mode in ['subscriber', 'both']
        
        # Publisher settings
        self.topic_prefix = cfg.get('topic_prefix', 'nettemp')
        self.qos = int(cfg.get('qos', 0))
        self.retain = bool(cfg.get('retain', False))
        
        # Subscriber settings
        self.subscribe_topics = cfg.get('subscribe_topics', [])
        if isinstance(self.subscribe_topics, str):
            self.subscribe_topics = [self.subscribe_topics]
        self.auth_token = cfg.get('auth_token')
        self.servers = cfg.get('servers', [])  # Server filtering for subscriber mode
        
        # Topic logging subscription (for autodiscovery assistance)
        self.topic_log_subscribe_topics = cfg.get('topic_log_subscribe_topics', [])
        if isinstance(self.topic_log_subscribe_topics, str):
            self.topic_log_subscribe_topics = [self.topic_log_subscribe_topics]
        # Default to lightweight BLE topic logging if not configured.
        if not self.topic_log_subscribe_topics:
            self.topic_log_subscribe_topics = ['home/+/BTtoMQTT/+']
        
        # Message parser (load early to get exclude_topics from rules file)
        self.parser = MQTTParser()  # Loads rules from mqtt_rules.yaml
        
        # Track last forward time per sensor_id for interval limiting
        self.last_forward_time = {}
        
        # Exclude topics - from config or from parser rules file
        self.exclude_topics = cfg.get('exclude_topics', [])
        if isinstance(self.exclude_topics, str):
            self.exclude_topics = [self.exclude_topics]
        
        # Topic logging for autodiscovery assistance (runtime/state dir)
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        self.topic_log_file = get_mqtt_topic_log_file()
        self.logged_topics = set()
        self._load_logged_topics()
        
        # If no exclude_topics in config, use ones from mqtt_rules.yaml
        if not self.exclude_topics and self.parser.exclude_topics:
            self.exclude_topics = self.parser.exclude_topics
            logging.info(f'Using {len(self.exclude_topics)} exclude patterns from mqtt_rules.yaml')
        
        # Validation
        if not self.broker:
            logging.error('MQTT broker not configured - disabling MQTT')
            self.enabled = False
            return
        
        if self.mode_subscriber and not self.subscribe_topics:
            logging.warning('MQTT subscriber mode enabled but no topics configured')
            self.mode_subscriber = False
        
        # MQTT client
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.reconnect_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

    def start(self):
        """Start MQTT connection"""
        if not self.enabled or not MQTT_AVAILABLE:
            return
        
        try:
            # Create MQTT client
            self.client = mqtt.Client(client_id=f'nettemp_{self.default_device_id}')
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Authentication
            if self.username:
                self.client.username_pw_set(self.username, self.password)
            
            # TLS/SSL
            if self.use_tls:
                self.client.tls_set()
            
            # Connect
            logging.info(f'Connecting to MQTT broker {self.broker}:{self.port}...')
            self.client.connect_async(self.broker, self.port, self.keepalive)
            self.client.loop_start()
            
        except Exception as e:
            logging.error(f'Failed to start MQTT client: {e}')
            self.enabled = False

    def stop(self):
        """Stop MQTT connection"""
        if not self.client:
            return
        
        logging.info('Stopping MQTT bridge')
        self.stop_event.set()
        
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            logging.error(f'Error stopping MQTT client: {e}')
        
        self.client = None
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.connected = True
            modes = []
            if self.mode_publisher:
                modes.append('publisher')
            if self.mode_subscriber:
                modes.append('subscriber')
            mode_str = '+'.join(modes)
            logging.info(f'MQTT connected to {self.broker}:{self.port} (mode: {mode_str})')
            
            # Subscribe to topic logging filters (always, even in publisher-only mode).
            for topic in self.topic_log_subscribe_topics:
                if not topic:
                    continue
                try:
                    client.subscribe(topic, qos=self.qos)
                    logging.info(f'MQTT subscribed (topic log): {topic}')
                except Exception as e:
                    logging.error(f'Failed to subscribe (topic log) to {topic}: {e}')

            # Subscribe to topics if in subscriber mode
            if self.mode_subscriber:
                for topic in self.subscribe_topics:
                    try:
                        client.subscribe(topic, qos=self.qos)
                        logging.info(f'MQTT subscribed to: {topic}')
                    except Exception as e:
                        logging.error(f'Failed to subscribe to {topic}: {e}')
        else:
            error_messages = {
                1: 'Connection refused - incorrect protocol version',
                2: 'Connection refused - invalid client identifier',
                3: 'Connection refused - server unavailable',
                4: 'Connection refused - bad username or password',
                5: 'Connection refused - not authorized'
            }
            msg = error_messages.get(rc, f'Connection failed with code {rc}')
            logging.error(f'MQTT connection failed: {msg}')
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.connected = False
        if rc != 0:
            logging.warning(f'MQTT disconnected unexpectedly (code {rc}), reconnecting...')

    def _on_message(self, client, userdata, msg):
        """Callback when message received (subscriber mode)"""
        try:
            topic = msg.topic
            
            # Check if topic should be excluded (e.g., nettemp/* to avoid loops)
            if self._should_exclude_topic(topic):
                logging.debug(f'MQTT ignoring excluded topic: {topic}')
                return
            
            payload_str = msg.payload.decode('utf-8') if isinstance(msg.payload, bytes) else msg.payload
            logging.debug(f'MQTT received on {topic}: {payload_str}')
            
            # Log topic for autodiscovery assistance
            self._log_topic(topic)

            # If subscriber mode is disabled, do not parse/forward (logging-only).
            if not self.mode_subscriber:
                return
            
            # Parse message using rule-based parser
            readings = self.parser.parse(topic, msg.payload)
            
            if not readings:
                # Use debug level instead of warning to reduce log spam
                # Parser already logs specific reasons (skip, whitelist, no match)
                logging.debug(f'No readings extracted from {topic}')
                return
            
            # Apply interval filtering
            now = time.time()
            filtered_readings = []
            
            for reading in readings:
                sensor_id = reading.get('sensor_id')
                interval = reading.get('interval', 0)
                
                if interval == 0:
                    # No interval limit - forward immediately
                    filtered_readings.append(reading)
                else:
                    # Check if enough time has passed
                    last_time = self.last_forward_time.get(sensor_id, 0)
                    time_elapsed = now - last_time
                    
                    if time_elapsed >= interval:
                        filtered_readings.append(reading)
                        self.last_forward_time[sensor_id] = now
                    else:
                        logging.debug(f'Throttling {sensor_id} - last forward was {int(time_elapsed)}s ago (interval: {interval}s)')
            
            if not filtered_readings:
                logging.debug(f'All {len(readings)} reading(s) from {topic} throttled by interval')
                return
            
            # Forward filtered readings to cloud servers
            success = self._forward_parsed_readings(filtered_readings)
            
            if success:
                logging.info(f'MQTT→Cloud: {topic} forwarded {len(filtered_readings)} reading(s) successfully')
            else:
                logging.warning(f'MQTT→Cloud: Failed to forward {topic}')
                
        except Exception as e:
            logging.error(f'Error processing MQTT message from {msg.topic}: {e}')
    
    def _load_logged_topics(self):
        """Load previously logged topics from file"""
        try:
            if self.topic_log_file.exists():
                with open(self.topic_log_file, 'r') as f:
                    self.logged_topics = set(line.strip() for line in f if line.strip())
        except Exception as e:
            logging.debug(f'Could not load topic log: {e}')
    
    def _log_topic(self, topic: str):
        """Log a unique topic to file for autodiscovery assistance"""
        if topic not in self.logged_topics:
            self.logged_topics.add(topic)
            try:
                with open(self.topic_log_file, 'a') as f:
                    f.write(f"{topic}\n")
            except Exception as e:
                logging.debug(f'Could not write to topic log: {e}')

    def _forward_parsed_readings(self, readings: list) -> bool:
        """
        Forward parsed readings to cloud servers
        
        Args:
            readings: List of readings from parser, each containing:
                - device_id: Device identifier
                - sensor_id: Unique sensor identifier  
                - sensor_type: Type of reading (temperature, humidity, etc.)
                - value: Numeric value
                - unit: Unit string
                - friendly_name: Display name
                
        Returns:
            True if successfully sent to at least one server
        """
        try:
            if not readings:
                return False
            
            # Group readings by device_id
            devices = {}
            for reading in readings:
                device_id = reading.get('device_id', self.default_device_id)
                if device_id not in devices:
                    devices[device_id] = []
                devices[device_id].append(reading)
            
            # Get target servers based on MQTT subscriber configuration
            if self.servers:
                # Filter to specific servers
                target_servers = [s for s in self.cloud_client.cloud_servers 
                                if s.get('enabled', True) and s.get('name') in self.servers]
                if not target_servers:
                    logging.warning(f'MQTT: No matching servers found for {self.servers}')
                    return False
            else:
                # Send to all enabled servers
                target_servers = [s for s in self.cloud_client.cloud_servers 
                                if s.get('enabled', True)]
            
            # Send each device's readings to target servers
            any_success = False
            for device_id, device_readings in devices.items():
                # Build cloud format payload
                cloud_payload = {
                    'device_id': device_id,
                    'readings': []
                }
                
                # Build legacy format payload
                legacy_payload = []
                
                for reading in device_readings:
                    sensor_id = reading.get('sensor_id')
                    sensor_type = reading.get('sensor_type', 'value')
                    value = reading.get('value')
                    unit = reading.get('unit', '')
                    friendly_name = reading.get('friendly_name', sensor_type)
                    
                    # Cloud format
                    cloud_payload['readings'].append({
                        'sensor_id': sensor_id,
                        'sensor_type': sensor_type,
                        'value': value,
                        'timestamp': int(time.time()),
                        'metadata': {
                            'name': friendly_name,
                            'unit': unit
                        }
                    })
                    
                    # Legacy format
                    legacy_payload.append({
                        'rom': sensor_id,
                        'type': sensor_type,
                        'value': value,
                        'unit': unit,
                        'name': friendly_name
                    })
                
                # Send to each target server in the correct format
                for server in target_servers:
                    server_format = server.get('format', 'cloud')
                    if server_format == 'legacy':
                        success = self.cloud_client._send_to_server_legacy(legacy_payload, server)
                    else:
                        success = self.cloud_client._send_to_server(cloud_payload, server)
                    
                    if success:
                        any_success = True
                        logging.debug(f"MQTT→Cloud: Forwarded {len(device_readings)} reading(s) from {device_id} to {server.get('name', 'server')}")
            
            return any_success
            
        except Exception as e:
            logging.error(f'Failed to forward parsed readings to cloud: {e}')
            return False

    def _should_exclude_topic(self, topic: str) -> bool:
        """Check if topic matches exclusion patterns"""
        for pattern in self.exclude_topics:
            # Use same matching logic as parser
            if pattern == '*' or pattern == '#':
                return True
            
            # Escape special regex characters but preserve wildcards
            escaped_pattern = pattern.replace('*', '<<<STAR>>>')
            escaped_pattern = escaped_pattern.replace('+', '<<<PLUS>>>')
            escaped_pattern = escaped_pattern.replace('#', '<<<HASH>>>')
            
            # Escape regex special characters
            escaped_pattern = re.escape(escaped_pattern)
            
            # Convert MQTT wildcards to regex
            escaped_pattern = escaped_pattern.replace('<<<STAR>>>', '[^/]+')   # * = single level
            escaped_pattern = escaped_pattern.replace('<<<PLUS>>>', '[^/]+')   # + = single level
            escaped_pattern = escaped_pattern.replace('<<<HASH>>>', '.*')      # # = multi level
            
            regex_pattern = '^' + escaped_pattern + '$'
            
            if re.match(regex_pattern, topic):
                return True
        
        return False

    def _parse_simple_message(self, topic: str, value_str: str) -> Optional[dict]:
        """Parse simple MQTT message (non-JSON) into reading format
        
        Supports ESPEasy format: device/task/valuename value
        Example: ESPEasyMega_1/system/rssi -55
        """
        try:
            # Parse topic - ESPEasy format: device/task/valuename
            parts = topic.split('/')
            
            # Skip status/control topics (LWT, status, etc.)
            if len(parts) >= 2 and parts[1].lower() in ['status', 'lwt', 'control', 'cmd']:
                logging.debug(f'Skipping status/control topic: {topic}')
                return None
            
            # Try to parse value
            try:
                value = float(value_str.strip())
            except ValueError:
                # If it's not a number and looks like status text, skip it
                if value_str.strip().lower() in ['connected', 'disconnected', 'online', 'offline']:
                    logging.debug(f'Skipping status message: {topic} = {value_str}')
                    return None
                value = value_str.strip()
            
            if len(parts) >= 3:
                # ESPEasy format: device/task/valuename
                device_name = parts[0]
                task = parts[1]
                valuename = parts[2]
                
                # Build sensor_id
                sensor_id = f'{device_name}_{task}_{valuename}'
                
                # Create friendly name
                friendly_name = ' '.join(word.capitalize() for word in valuename.replace('_', ' ').split())
                if task:
                    friendly_name = f'{task.capitalize()} {friendly_name}'
                
                # Return dict with device_id and readings for cloud format
                return {
                    'device_id': device_name,
                    'sensor_id': sensor_id,
                    'sensor_type': valuename,
                    'task': task,
                    'value': value,
                    'friendly_name': friendly_name
                }
            elif len(parts) == 2:
                # Simple format: device/sensor
                device_name = parts[0]
                sensor_name = parts[1]
                
                sensor_id = f'{device_name}_{sensor_name}'
                friendly_name = sensor_name.replace('_', ' ').capitalize()
                
                return {
                    'device_id': device_name,
                    'sensor_id': sensor_id,
                    'sensor_type': sensor_name,
                    'value': value,
                    'friendly_name': friendly_name
                }
            else:
                # Fallback: use topic as sensor
                sensor_id = topic.replace('/', '_')
                return {
                    'device_id': self.default_device_id,
                    'sensor_id': sensor_id,
                    'sensor_type': 'value',
                    'value': value,
                    'friendly_name': topic
                }
        except Exception as e:
            logging.error(f'Error parsing simple MQTT message: {e}')
            return None

    def _forward_to_cloud(self, payload: Any) -> bool:
        """Forward received MQTT message to cloud servers
        
        Sends in two formats:
        1. Legacy format for Docker: insert2([{rom, type, value, name}])
        2. Cloud format: send_payload({device_id, readings: [{sensor_id, sensor_type, value, metadata}]})
        """
        try:
            # Handle parsed ESPEasy format from _parse_simple_message
            if isinstance(payload, dict) and 'device_id' in payload and 'sensor_id' in payload:
                device_id = payload['device_id']
                sensor_id = payload['sensor_id']
                sensor_type = payload.get('sensor_type', 'value')
                value = payload['value']
                friendly_name = payload.get('friendly_name', sensor_type)
                task = payload.get('task', '')
                
                # Legacy format for Docker
                legacy_payload = [{
                    'rom': sensor_id,
                    'type': sensor_type,
                    'value': value,
                    'name': f'{task}/{sensor_type}' if task else sensor_type
                }]
                
                # Cloud format
                cloud_payload = {
                    'device_id': device_id,
                    'readings': [{
                        'sensor_id': sensor_id,
                        'sensor_type': sensor_type,
                        'value': value,
                        'timestamp': int(time.time()),
                        'metadata': {
                            'name': friendly_name
                        }
                    }]
                }
                
                # Get target servers based on MQTT subscriber configuration
                if self.servers:
                    # Filter to specific servers
                    target_servers = [s for s in self.cloud_client.cloud_servers 
                                    if s.get('enabled', True) and s.get('name') in self.servers]
                    if not target_servers:
                        logging.warning(f'MQTT: No matching servers found for {self.servers}')
                        return False
                else:
                    # Send to all enabled servers
                    target_servers = [s for s in self.cloud_client.cloud_servers 
                                    if s.get('enabled', True)]
                
                # Send to each target server in the correct format
                any_success = False
                for server in target_servers:
                    server_format = server.get('format', 'cloud')
                    if server_format == 'legacy':
                        # Send legacy format: insert2([{rom, type, value, name}])
                        success = self.cloud_client._send_to_server_legacy(legacy_payload, server)
                    else:
                        # Send cloud format: {device_id, readings: [...]}
                        success = self.cloud_client._send_to_server(cloud_payload, server)
                    
                    if success:
                        any_success = True
                
                return any_success
            
            # Get target servers based on MQTT subscriber configuration (for other payload types)
            if self.servers:
                # Filter to specific servers
                target_servers = [s for s in self.cloud_client.cloud_servers 
                                if s.get('enabled', True) and s.get('name') in self.servers]
                if not target_servers:
                    logging.warning(f'MQTT: No matching servers found for {self.servers}')
                    return False
            else:
                # Send to all enabled servers
                target_servers = [s for s in self.cloud_client.cloud_servers 
                                if s.get('enabled', True)]
            
            # Handle different payload formats
            readings = None
            if isinstance(payload, list):
                # List of readings
                readings = payload
            elif isinstance(payload, dict):
                # Check if it's a readings wrapper
                if 'readings' in payload:
                    readings = payload.get('readings', [])
                # Check if it's a single reading
                elif 'rom' in payload or 'type' in payload:
                    readings = [payload]
                # Try to convert dict to reading
                else:
                    reading = self._dict_to_reading(payload)
                    if reading:
                        readings = [reading]
            
            if not readings:
                logging.warning(f'Unknown MQTT payload format: {type(payload)}')
                return False
            
            # Transform to cloud format
            cloud_data = self.cloud_client._transform_data(readings)
            if not cloud_data or not cloud_data.get('readings'):
                return False
            
            # Send to each target server
            any_success = False
            for server in target_servers:
                server_format = server.get('format', 'cloud')
                if server_format == 'legacy':
                    success = self.cloud_client._send_to_server_legacy(readings, server)
                else:
                    success = self.cloud_client._send_to_server(cloud_data, server)
                
                if success:
                    any_success = True
                    logging.debug(f"MQTT→Cloud: Forwarded to {server.get('name', 'server')}")
            
            return any_success
            
        except Exception as e:
            logging.error(f'Failed to forward MQTT message to cloud: {e}')
            return False

    def _dict_to_reading(self, data: dict) -> Optional[dict]:
        """Convert generic dict to reading format"""
        try:
            # Try to extract common fields
            sensor_id = data.get('sensor_id') or data.get('sensor') or data.get('id') or 'mqtt_sensor'
            value = data.get('value') or data.get('val') or data.get('v')
            reading_type = data.get('type') or data.get('t') or 'value'
            unit = data.get('unit') or data.get('u') or ''
            
            if value is None:
                return None
            
            return {
                'rom': sensor_id,
                'type': reading_type,
                'value': float(value),
                'unit': unit,
                'name': f'{sensor_id}/{reading_type}'
            }
        except Exception:
            return None

    def publish_readings(self, readings: list, group_id: str = None) -> bool:
        """Publish sensor readings to MQTT (publisher mode)"""
        if not self.enabled or not self.mode_publisher or not self.connected:
            return False
        
        if not readings:
            return True
        
        group = group_id or self.default_device_id
        success_count = 0
        
        for reading in readings:
            try:
                sensor_id = reading.get('rom', 'unknown')
                reading_type = reading.get('type', 'value')
                value = reading.get('value')
                
                # Build topic: nettemp/{group}/{sensor_id}/{type}
                topic = f'{self.topic_prefix}/{group}/{sensor_id}/{reading_type}'
                
                # Prepare payload
                payload = {
                    'value': value,
                    'type': reading_type,
                    'sensor_id': sensor_id,
                    'timestamp': int(time.time())
                }
                
                # Add optional fields
                if 'unit' in reading:
                    payload['unit'] = reading['unit']
                if 'name' in reading:
                    payload['name'] = reading['name']
                
                # Publish
                result = self.client.publish(
                    topic,
                    json.dumps(payload),
                    qos=self.qos,
                    retain=self.retain
                )
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    success_count += 1
                    logging.debug(f'MQTT published: {topic} = {value}')
                else:
                    logging.warning(f'MQTT publish failed for {topic}: {result.rc}')
                    
            except Exception as e:
                logging.error(f'Error publishing reading to MQTT: {e}')
        
        return success_count > 0

    def is_connected(self) -> bool:
        """Check if MQTT client is connected"""
        return self.connected and self.client is not None

"""
MQTT Message Parsers
Parses MQTT messages from various IoT devices based on rules defined in mqtt_rules.yaml
"""

import re
import json
import logging
from typing import Optional, Any
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None


class MQTTParser:
    """Rule-based MQTT message parser"""
    
    def __init__(self, rules_file: str = None):
        """
        Initialize parser with rules from YAML file
        
        Args:
            rules_file: Path to mqtt_rules.yaml (defaults to same directory as this file)
        """
        self.rules = []
        self.exclude_topics = []
        self.discovered_devices = set()  # Track discovered devices to avoid duplicate logs
        
        if not YAML_AVAILABLE:
            logging.warning('YAML support not available - install PyYAML: pip install pyyaml')
            return
        
        if not rules_file:
            # Default to mqtt_rules.yaml in parent directory (client root)
            rules_file = Path(__file__).parent.parent / 'mqtt_rules.yaml'
        
        try:
            with open(rules_file, 'r') as f:
                config = yaml.safe_load(f)
                self.rules = config.get('rules', [])
                self.exclude_topics = config.get('exclude_topics', [])
                logging.info(f'Loaded {len(self.rules)} MQTT parsing rules from {rules_file}')
                if self.exclude_topics:
                    logging.info(f'Loaded {len(self.exclude_topics)} exclude patterns from {rules_file}')
        except FileNotFoundError:
            logging.warning(f'MQTT rules file not found: {rules_file}')
        except Exception as e:
            logging.error(f'Failed to load MQTT rules: {e}')
    
    def parse(self, topic: str, payload: str | bytes) -> Optional[list]:
        """
        Parse MQTT message into list of readings
        
        Args:
            topic: MQTT topic
            payload: Message payload (string or bytes)
            
        Returns:
            List of readings in format:
            [{
                'device_id': 'device_name',
                'sensor_id': 'unique_sensor_id', 
                'sensor_type': 'temperature',
                'value': 22.5,
                'unit': '°C',
                'friendly_name': 'Living Room Temperature'
            }]
            
            Returns None if message cannot be parsed
        """
        if not self.rules:
            logging.debug('No MQTT rules loaded')
            return None
        
        # Decode payload if bytes
        if isinstance(payload, bytes):
            try:
                payload = payload.decode('utf-8')
            except UnicodeDecodeError:
                logging.warning(f'Failed to decode payload from {topic}')
                return None
        
        # Try each rule in order
        for rule in self.rules:
            if not rule.get('enabled', True):
                continue
            
            # Check if topic matches pattern
            if not self._topic_matches(topic, rule.get('topic_pattern', '*')):
                continue
            
            # Check skip rules
            if self._should_skip_topic(topic, rule.get('skip_topics', [])):
                logging.debug(f'Skipping topic {topic} (matched skip rule)')
                continue
            
            # Pre-check whitelist for JSON messages to avoid parsing non-whitelisted devices
            allowed_devices = rule.get('allowed_devices', [])
            if allowed_devices and rule.get('format') == 'json':
                try:
                    import json as json_module
                    data = json_module.loads(payload)
                    if isinstance(data, dict):
                        device_mac = data.get('id', '')
                        device_name = data.get(rule.get('device_id_field', 'device_id'), '')
                        
                        # Check if device is in whitelist
                        if device_mac not in allowed_devices and device_name not in allowed_devices:
                            logging.debug(f'Skipping non-whitelisted device on {topic}: mac={device_mac}, name={device_name}')
                            continue
                except:
                    pass  # If pre-check fails, let normal parsing handle it
            
            # Try to parse with this rule
            try:
                readings = self._parse_with_rule(topic, payload, rule)
                if readings:
                    logging.debug(f'Parsed {topic} with rule: {rule.get("name")}')
                    return readings
                else:
                    # No readings extracted (but parsing didn't error)
                    logging.debug(f'No readings extracted from {topic} with rule: {rule.get("name")}')
            except Exception as e:
                logging.error(f'Error parsing {topic} with rule {rule.get("name")}: {e}')
                continue
        
        logging.debug(f'No matching rule for topic: {topic}')
        return None
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches MQTT wildcard pattern"""
        if pattern == '*' or pattern == '#':
            return True
        
        # Escape special regex characters first, but preserve our wildcards
        # Replace * with placeholder, escape everything, then restore wildcards
        pattern = pattern.replace('*', '<<<STAR>>>')
        pattern = pattern.replace('+', '<<<PLUS>>>')
        pattern = pattern.replace('#', '<<<HASH>>>')
        
        # Escape regex special characters
        pattern = re.escape(pattern)
        
        # Convert MQTT wildcards to regex
        pattern = pattern.replace('<<<STAR>>>', '[^/]+')   # * = single level wildcard
        pattern = pattern.replace('<<<PLUS>>>', '[^/]+')   # + = single level wildcard
        pattern = pattern.replace('<<<HASH>>>', '.*')      # # = multi level wildcard
        
        regex_pattern = '^' + pattern + '$'
        
        return bool(re.match(regex_pattern, topic))
    
    def _should_skip_topic(self, topic: str, skip_patterns: list) -> bool:
        """Check if topic matches any skip pattern"""
        for pattern in skip_patterns:
            if self._topic_matches(topic, pattern):
                return True
        return False
    
    def _parse_with_rule(self, topic: str, payload: str, rule: dict) -> Optional[list]:
        """Parse message using specific rule"""
        format_type = rule.get('format', 'json')
        
        if format_type == 'json':
            return self._parse_json(topic, payload, rule)
        elif format_type == 'value':
            return self._parse_value(topic, payload, rule)
        else:
            logging.warning(f'Unknown format type: {format_type}')
            return None
    
    def _parse_json(self, topic: str, payload: str, rule: dict) -> Optional[list]:
        """Parse JSON payload"""
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None
        
        if not isinstance(data, dict):
            return None
        
        # Extract device_id
        device_id = self._extract_device_id(topic, data, rule)
        if not device_id:
            logging.debug(f'Could not extract device_id from {topic}')
            return None
        
        # Autodiscovery mode - log all devices
        if rule.get('autodiscover', False):
            self._log_discovered_device(topic, device_id, data, rule)
        
        # Whitelist filtering - only allow specified devices
        allowed_devices = rule.get('allowed_devices', [])
        if allowed_devices:
            # Check device_id against whitelist (match name or id field)
            device_name = data.get(rule.get('device_id_field', 'device_id'), '')
            device_mac = data.get('id', '')
            
            if device_id not in allowed_devices and device_name not in allowed_devices and device_mac not in allowed_devices:
                logging.debug(f'Skipping non-whitelisted device: {device_id} (name={device_name}, mac={device_mac})')
                return None
        
        # Get friendly name prefix
        friendly_name_prefix = data.get(rule.get('friendly_name_field', 'name'), '')
        
        # Flatten nested JSON if requested
        if rule.get('flatten_nested', False):
            data = self._flatten_dict(data)
        
        # Extract readings based on readings_map
        readings_map = rule.get('readings_map', {})
        if not readings_map:
            return None
        
        readings = []
        for field, config in readings_map.items():
            # Check if field exists in data
            value = data.get(field)
            if value is None:
                continue
            
            # Skip certain values
            skip_values = rule.get('skip_values', [])
            if value in skip_values or str(value).lower() in [s.lower() for s in skip_values]:
                continue
            
            # Get sensor type
            sensor_type = config.get('type')
            if not sensor_type:
                # Try to get type from field
                type_field = config.get('type_from_field')
                if type_field:
                    sensor_type = data.get(type_field, field)
                else:
                    sensor_type = field
            
            # Get unit
            unit = config.get('unit', '')
            unit_field = config.get('unit_from_field')
            if unit_field:
                unit_value = data.get(unit_field)
                if unit_value:
                    # Map unit value if mapping provided
                    unit_map = config.get('unit_map', {})
                    unit = unit_map.get(unit_value, unit_value)
            
            # Apply value mapping if provided
            value_map = config.get('value_map', {})
            if value_map:
                if value in value_map:
                    value = value_map[value]
                elif str(value) in value_map:
                    value = value_map[str(value)]
            
            # Convert value to float if possible
            try:
                value = float(value)
            except (ValueError, TypeError):
                # Keep as-is if not numeric
                pass
            
            # Build sensor_id
            sensor_id_field = rule.get('sensor_id_field')
            if sensor_id_field:
                sensor_id = data.get(sensor_id_field, f'{device_id}_{field}')
            else:
                sensor_id = f'{device_id}_{field}'
            
            # Clean sensor_id (replace special chars with underscore)
            sensor_id = re.sub(r'[^a-zA-Z0-9_-]', '_', sensor_id)
            
            # Build friendly name
            # Check for sensor_name_field (overrides everything - just shows the field value)
            sensor_name_field = rule.get('sensor_name_field')
            if sensor_name_field:
                # Use specific field as the complete sensor name (e.g., "type" field = "THB")
                friendly_name = data.get(sensor_name_field, sensor_type)
            elif rule.get('display_name_field'):
                # Use specific field for display name prefix (e.g., "name" for "ATC_165B5D")
                display_name_field = rule.get('display_name_field')
                display_prefix = data.get(display_name_field, '')
                if display_prefix:
                    friendly_name = f'{display_prefix} {sensor_type}'
                else:
                    friendly_name = f'{device_id} {sensor_type}'
            elif friendly_name_prefix:
                friendly_name = f'{friendly_name_prefix} {sensor_type}'
            else:
                # No prefix - show just the sensor type
                friendly_name = sensor_type
            
            readings.append({
                'device_id': device_id,
                'sensor_id': sensor_id,
                'sensor_type': sensor_type,
                'value': value,
                'unit': unit,
                'friendly_name': friendly_name,
                'interval': rule.get('interval', 0)  # Forward interval from rule
            })
        
        return readings if readings else None
    
    def _parse_value(self, topic: str, payload: str, rule: dict) -> Optional[list]:
        """Parse simple value payload (non-JSON)"""
        # Skip certain values
        skip_values = rule.get('skip_values', [])
        if payload.strip() in skip_values or payload.strip().lower() in [s.lower() for s in skip_values]:
            logging.debug(f'Skipping value: {payload}')
            return None
        
        # Try to parse as number
        try:
            value = float(payload.strip())
        except ValueError:
            # Not a number - could be string status
            return None
        
        # Extract device_id from topic
        device_id = self._extract_device_id(topic, {}, rule)
        if not device_id:
            return None
        
        # Parse topic parts
        topic_parts = topic.split('/')
        
        # Build sensor_id based on format
        sensor_id_format = rule.get('sensor_id_format', 'topic_full')
        
        if sensor_id_format == 'topic_full':
            sensor_id = topic.replace('/', '_')
        elif '{' in sensor_id_format:
            # Template format like "{device}_{task}_{valuename}"
            replacements = {
                'device': topic_parts[0] if len(topic_parts) > 0 else '',
                'task': topic_parts[1] if len(topic_parts) > 1 else '',
                'valuename': topic_parts[2] if len(topic_parts) > 2 else '',
                'type': topic_parts[-1] if topic_parts else '',
                'object_id': topic_parts[-2] if len(topic_parts) > 1 else ''
            }
            sensor_id = sensor_id_format.format(**replacements)
        else:
            sensor_id = f'{device_id}_{topic_parts[-1] if topic_parts else "value"}'
        
        # Clean sensor_id
        sensor_id = re.sub(r'[^a-zA-Z0-9_-]', '_', sensor_id)
        
        # Get sensor type
        value_type = rule.get('value_type', 'value')
        value_type_from = rule.get('value_type_from')
        
        if value_type_from == 'valuename' and len(topic_parts) >= 3:
            value_type = topic_parts[2]
        elif value_type_from == 'component' and len(topic_parts) >= 2:
            value_type = topic_parts[1]
        elif value_type_from == 'topic' and topic_parts:
            value_type = topic_parts[-1]
        
        # Build friendly name
        friendly_name_format = rule.get('friendly_name_format')
        if friendly_name_format and '{' in friendly_name_format:
            replacements = {
                'device': topic_parts[0] if len(topic_parts) > 0 else '',
                'task': topic_parts[1] if len(topic_parts) > 1 else '',
                'valuename': topic_parts[2] if len(topic_parts) > 2 else ''
            }
            friendly_name = friendly_name_format.format(**replacements)
        else:
            friendly_name = f'{device_id} {value_type}'
        
        return [{
            'device_id': device_id,
            'sensor_id': sensor_id,
            'sensor_type': value_type,
            'value': value,
            'unit': '',
            'friendly_name': friendly_name,
            'interval': rule.get('interval', 0)  # Forward interval from rule
        }]
    
    def _extract_device_id(self, topic: str, data: dict, rule: dict) -> Optional[str]:
        """Extract device ID from topic or JSON data"""
        # Try to get from JSON field first
        device_id_field = rule.get('device_id_field')
        if device_id_field and data:
            device_id = data.get(device_id_field)
            if device_id:
                return self._clean_device_id(device_id)
        
        # Try fallback field
        device_id_fallback = rule.get('device_id_fallback')
        if device_id_fallback and data:
            device_id = data.get(device_id_fallback)
            if device_id:
                return self._clean_device_id(device_id)
        
        # Extract from topic
        device_id_from = rule.get('device_id_from')
        if device_id_from == 'topic':
            topic_parts = topic.split('/')
            if topic_parts:
                # Use first non-empty part as device
                return self._clean_device_id(topic_parts[0])
        
        return None
    
    def _log_discovered_device(self, topic: str, device_id: str, data: dict, rule: dict):
        """Log discovered device for autodiscovery"""
        try:
            # Extract useful info
            device_name = data.get(rule.get('device_id_field', 'device_id'), 'unknown')
            device_mac = data.get('id', 'unknown')
            
            # Create unique key to avoid duplicate logs
            device_key = f"{device_mac}:{device_name}"
            
            # Skip if already logged
            if device_key in self.discovered_devices:
                return
            
            self.discovered_devices.add(device_key)
            
            log_file = Path(__file__).parent / 'mqtt_discovered_devices.log'
            
            device_type = data.get('type', 'unknown')
            brand = data.get('brand', 'unknown')
            model = data.get('model', 'unknown')
            
            # Get available sensor fields (exclude metadata)
            metadata_fields = {'id', 'name', 'rssi', 'brand', 'model', 'model_id', 'type', 'mac', 'mfr', 'manufacturerdata'}
            sensor_fields = [k for k in data.keys() if k not in metadata_fields]
            
            log_entry = (
                f"{topic} | "
                f"device_id={device_id} | "
                f"name={device_name} | "
                f"mac={device_mac} | "
                f"type={device_type} | "
                f"brand={brand} | "
                f"model={model} | "
                f"sensors={','.join(sensor_fields) if sensor_fields else 'none'}\n"
            )
            
            # Append to log file
            with open(log_file, 'a') as f:
                f.write(log_entry)
            
            logging.info(f'Discovered new device: {device_name} ({device_mac}) with sensors: {sensor_fields}')
                
        except Exception as e:
            logging.warning(f'Failed to log discovered device: {e}')
    
    def _clean_device_id(self, device_id: str) -> str:
        """Clean device ID - replace special chars"""
        # Replace colons and other special chars with underscores
        return re.sub(r'[^a-zA-Z0-9_-]', '_', str(device_id))
    
    def _flatten_dict(self, data: dict, parent_key: str = '', sep: str = '.') -> dict:
        """Flatten nested dictionary"""
        items = []
        for k, v in data.items():
            new_key = f'{parent_key}{sep}{k}' if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

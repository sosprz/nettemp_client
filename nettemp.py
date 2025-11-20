"""
Nettemp Cloud Client - Send sensor data to cloud API
"""
import requests
import time
import json
import hashlib
import sqlite3
import os
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path


class CloudClient:
    """Lightweight cloud client for Nettemp - supports multiple cloud servers"""

    def __init__(self, config_path: str = "config.conf"):
        self.config = self._load_config(config_path)
        self.device_id = self.config.get('group', 'unknown')

        # Support both single cloud server (backward compatible) and multiple servers
        self.cloud_servers = self._parse_cloud_servers()

        self.timeout = 10
        self.retry_attempts = 3

        # Local buffer for offline storage (shared across all servers)
        self.buffer_db = Path(config_path).parent / 'cloud_buffer.db'
        self._init_buffer()

    def _parse_cloud_servers(self) -> List[Dict[str, Any]]:
        """Parse cloud server configurations - supports both single and multiple servers"""
        servers = []

        # Option 1: New format with cloud_servers list
        if 'cloud_servers' in self.config and isinstance(self.config['cloud_servers'], list):
            for server in self.config['cloud_servers']:
                if isinstance(server, dict):
                    servers.append({
                        'url': server.get('url', '').rstrip('/'),
                        'api_key': server.get('api_key', ''),
                        'enabled': server.get('enabled', True),
                        'name': server.get('name', server.get('url', 'unnamed'))
                    })

        # Option 2: Backward compatible single cloud server
        if 'cloud_server' in self.config:
            url = self.config.get('cloud_server', '').rstrip('/')
            api_key = self.config.get('cloud_api_key', '')
            enabled = self.config.get('cloud_enabled', False)

            if url and api_key and enabled:
                servers.append({
                    'url': url,
                    'api_key': api_key,
                    'enabled': enabled,
                    'name': url
                })

        return [s for s in servers if s['enabled'] and s['url'] and s['api_key']]

    def _load_config(self, config_path: str) -> dict:
        """Load YAML config"""
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logging.error(f"Config load error: {e}")
            return {}

    def _init_buffer(self):
        """Initialize SQLite buffer for offline storage"""
        try:
            with sqlite3.connect(self.buffer_db, timeout=10) as conn:
                conn.execute('PRAGMA journal_mode=WAL;')
                conn.execute('PRAGMA busy_timeout=5000;')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS buffer (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data TEXT NOT NULL,
                        timestamp INTEGER NOT NULL,
                        attempts INTEGER DEFAULT 0
                    )
                ''')
                conn.commit()
        except Exception as e:
            logging.error(f"Buffer init error: {e}")

    def send(self, data: List[Dict]) -> bool:
        """
        Send data to all enabled cloud servers (works with old nettemp format)

        Args:
            data: List of dicts with keys: rom, type, value, name

        Returns:
            True if sent successfully to at least one server
        """
        if not self.cloud_servers:
            return False

        # Transform old format to cloud format once
        cloud_data = self._transform_data(data)
        readings = cloud_data.get('readings', []) or []
        if not readings:
            return False

        # Track if we successfully sent to at least one server
        any_success = False

        # Send to each enabled cloud server
        for server in self.cloud_servers:
            server_success = self._send_to_server(cloud_data, server)
            if server_success:
                any_success = True

        # Try to flush buffer if we had any success
        if any_success:
            self._flush_buffer()

        return any_success

    def send_payload(self, payload: Dict) -> bool:
        """
        Send already-transformed payload (device_id + readings) to all cloud servers.
        """
        if not self.cloud_servers:
            return False
        if not payload or not payload.get('readings'):
            return False

        any_success = False
        for server in self.cloud_servers:
            if self._send_to_cloud(payload, server):
                any_success = True

        if any_success:
            self._flush_buffer()

        return any_success

    def _send_to_server(self, cloud_data: Dict, server: Dict[str, str]) -> bool:
        """Send data to a specific cloud server"""
        # The cloud API accepts up to ~100 readings per request. Split into batches
        readings = cloud_data.get('readings', []) or []
        batch_size = 100
        total = len(readings)
        sent_all = True

        for i in range(0, total, batch_size):
            batch_readings = readings[i:i + batch_size]
            batch_data = {'device_id': cloud_data.get('device_id'), 'readings': batch_readings}

            success = self._send_to_cloud(batch_data, server)
            if not success:
                # Buffer this failed batch with server info
                self._add_to_buffer(batch_data, server)
                sent_all = False

        return sent_all

    def _transform_data(self, data: List[Dict]) -> Dict:
        """Transform old nettemp format to cloud format"""
        readings = []

        for item in data:
            # Parse old ROM format
            sensor_info = self._parse_rom(item.get('rom', ''))

            readings.append({
                'sensor_id': sensor_info['id'],
                'sensor_type': item.get('type', ''),  # Send as-is, backend normalizes
                'value': float(item.get('value', 0)),
                'unit': item.get('unit', ''),  # Send unit if provided, backend fills if empty
                'timestamp': int(time.time()),
                'metadata': {
                    'name': item.get('name', ''),
                    'original_rom': item.get('rom', '')
                }
            })

        return {
            'device_id': self.device_id,
            'readings': readings
        }

    def _parse_rom(self, rom: str) -> Dict[str, str]:
        """Parse old ROM format to extract sensor_id"""
        # Normalize ROM: strip any leading underscores (drivers often prefix roms with '_')
        # and remove group prefix if present.
        rom = (rom or '')
        group = None
        # If the rom starts with device/group, capture it and strip for parsing
        if self.device_id and rom.startswith(self.device_id):
            group = self.device_id
            rom = rom[len(self.device_id):]
        # Strip leading underscores that drivers commonly include
        rom = rom.lstrip('_')

        # DS18B20: 28-00000a1b2c
        if rom.startswith('28-'):
            if group:
                return {'id': f'{group}-{rom}', 'type': '1wire'}
            return {'id': rom, 'type': '1wire'}

        # DHT: _dht22_temp_gpio_D4
        if 'dht' in rom.lower():
            if 'D' in rom:
                pin = rom.split('_D')[1] if '_D' in rom else '0'
                sensor = 'dht22' if 'dht22' in rom.lower() else 'dht11'
                if group:
                    return {'id': f'{group}-{sensor}-gpio{pin}', 'type': 'gpio'}
                return {'id': f'{sensor}-gpio{pin}', 'type': 'gpio'}

        # I2C: allow patterns like '_i2c_76_temp' or '<driver>_i2c_76_temp'
        if 'i2c' in rom.lower():
            parts = rom.split('_')
            # find the 'i2c' token and capture the following address token
            for i, part in enumerate(parts):
                if part.lower() == 'i2c' and i + 1 < len(parts):
                    addr = parts[i + 1]
                    # If there's a token before 'i2c' that looks like a driver name, include it
                    driver = parts[i - 1] if i - 1 >= 0 and parts[i - 1] else None
                    if driver:
                        if group:
                            return {'id': f'{group}-{driver.lower()}-i2c-0x{addr}', 'type': 'i2c'}
                        return {'id': f'{driver.lower()}-i2c-0x{addr}', 'type': 'i2c'}
                    if group:
                        return {'id': f'{group}-i2c-0x{addr}', 'type': 'i2c'}
                    return {'id': f'i2c-0x{addr}', 'type': 'i2c'}

        # Fallback: use ROM as-is or hash
        if len(rom) > 20:
            hash_short = hashlib.md5(rom.encode()).hexdigest()[:8]
            if group:
                return {'id': f'{group}-sensor-{hash_short}', 'type': 'unknown'}
            return {'id': f'sensor-{hash_short}', 'type': 'unknown'}

        # If there's a group we captured earlier, prepend it to the id so
        # demo/group-prefixed ROMs yield IDs including the group.
        if group and rom:
            return {'id': f'{group}-{rom}', 'type': 'unknown'}

        return {'id': rom or 'unknown', 'type': 'unknown'}

    def _send_to_cloud(self, data: Dict, server: Dict[str, str]) -> bool:
        """Send data to specific cloud server"""
        url = server['url']
        api_key = server['api_key']
        name = server.get('name', url)

        for attempt in range(self.retry_attempts):
            try:
                # Create session for this specific server with its API key
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'NettempCloud/1.0',
                    'X-Readings-Count': str(len(data.get('readings', [])))
                }

                response = requests.post(
                    f'{url}/api/v1/data',
                    json=data,
                    headers=headers,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    logging.info(f"[Cloud:{name}] Sent {len(data.get('readings', []))} readings")
                    return True
                elif response.status_code == 401:
                    logging.error(f"[Cloud:{name}] Invalid API key")
                    return False
                elif response.status_code == 429:
                    logging.warning(f"[Cloud:{name}] Rate limited, retrying...")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    logging.error(f"[Cloud:{name}] Error {response.status_code}")

            except requests.exceptions.Timeout:
                logging.warning(f"[Cloud:{name}] Timeout (attempt {attempt + 1}/{self.retry_attempts})")
                if attempt < self.retry_attempts - 1:
                    time.sleep(1)
            except Exception as e:
                logging.error(f"[Cloud:{name}] Error: {e}")
                break

        return False

    def _add_to_buffer(self, data: Dict, server: Dict[str, str]):
        """Add failed data to local buffer with server info"""
        try:
            with sqlite3.connect(self.buffer_db, timeout=10) as conn:
                conn.execute('PRAGMA busy_timeout=5000;')
                buffer_entry = {
                    'data': data,
                    'server': server
                }
                conn.execute(
                    'INSERT INTO buffer (data, timestamp) VALUES (?, ?)',
                    (json.dumps(buffer_entry), int(time.time()))
                )
                conn.commit()
                logging.info(f"[Cloud:{server.get('name', server['url'])}] Buffered for retry")
        except Exception as e:
            logging.error(f"Buffer add error: {e}")

    def _flush_buffer(self):
        """Try to send buffered data to their respective servers"""
        try:
            with sqlite3.connect(self.buffer_db, timeout=10) as conn:
                conn.execute('PRAGMA busy_timeout=5000;')
                cursor = conn.execute(
                    'SELECT id, data FROM buffer WHERE attempts < 5 ORDER BY timestamp LIMIT 10'
                )
                rows = cursor.fetchall()

                for row_id, data_json in rows:
                    try:
                        buffer_entry = json.loads(data_json)

                        # Handle both old format (just data) and new format (data + server)
                        if isinstance(buffer_entry, dict) and 'server' in buffer_entry:
                            data = buffer_entry['data']
                            server = buffer_entry['server']
                        else:
                            # Old format - try first available server
                            data = buffer_entry
                            if not self.cloud_servers:
                                continue
                            server = self.cloud_servers[0]

                        if self._send_to_cloud(data, server):
                            conn.execute('DELETE FROM buffer WHERE id = ?', (row_id,))
                        else:
                            conn.execute(
                                'UPDATE buffer SET attempts = attempts + 1 WHERE id = ?',
                                (row_id,)
                            )
                    except Exception as e:
                        logging.error(f"Buffer flush item error: {e}")
                        continue

                conn.commit()
        except Exception as e:
            logging.error(f"Buffer flush error: {e}")

    def close(self):
        """Cleanup resources"""
        pass


# Backward compatible insert2 replacement
class insert2:
    """Drop-in replacement for old nettemp.insert2 with cloud support"""

    def __init__(self, data):
        self.data = data
        self._cloud_client = None

    def request(self):
        """Send to both local server and cloud"""
        import yaml
        import socket
        import os
        import inspect

        # Load config
        dir_path = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(dir_path, 'config.conf')

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
        except:
            logging.error("Cannot load config")
            return

        # Allow overriding the group via CLOUD_GROUP so callers (like the demo)
        # can force a single canonical device_id for both local and cloud sends.
        group = os.environ.get('CLOUD_GROUP', config.get('group', socket.gethostname()))

        # Add group to data
        for d in self.data:
            d['group'] = group
            # Avoid double-underscores when drivers supply roms that start with '_'.
            # Normalize by stripping leading underscores from rom before joining with group.
            rom_raw = d.get('rom', '') or ''
            if not rom_raw.startswith(group):
                d['rom'] = f"{group}_{rom_raw.lstrip('_')}"

        # 1. Send to old local server
        server = config.get('server')
        server_api_key = config.get('server_api_key')

        if server and server_api_key:
            try:
                requests.post(
                    server,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {server_api_key}'
                    },
                    json=self.data,
                    verify=False,
                    timeout=5
                )
                logging.info(f"[Local] Data sent")
            except Exception as e:
                logging.error(f"[Local] Cannot connect: {e}")

        # 2. Send to cloud (supports both single and multiple cloud servers)
        # CloudClient will check if any servers are configured and enabled
        try:
            if not self._cloud_client:
                self._cloud_client = CloudClient(config_file)

            # CloudClient.send() will return False if no servers configured
            if self._cloud_client.cloud_servers:
                if self._cloud_client.send(self.data):
                    logging.info(f"[Cloud] Data sent to {len(self._cloud_client.cloud_servers)} server(s)")
                else:
                    logging.warning(f"[Cloud] Some failures - check logs")
        except Exception as e:
            logging.error(f"[Cloud] Error: {e}")
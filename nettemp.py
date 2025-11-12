"""
Nettemp Cloud Client - Send sensor data to cloud API
"""
import requests
import time
import json
import hashlib
import sqlite3
import os
from typing import List, Dict, Optional, Any
from pathlib import Path


class CloudClient:
    """Lightweight cloud client for Nettemp"""

    def __init__(self, config_path: str = "config.conf"):
        self.config = self._load_config(config_path)
        self.device_id = self.config.get('group', 'unknown')
        self.cloud_url = self.config.get('cloud_server', '').rstrip('/')
        self.api_key = self.config.get('cloud_api_key', '')
        self.enabled = self.config.get('cloud_enabled', False)
        self.timeout = 10
        self.retry_attempts = 3

        # Local buffer for offline storage
        self.buffer_db = Path(config_path).parent / 'cloud_buffer.db'
        self._init_buffer()

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'NettempCloud/1.0'
        })

    def _load_config(self, config_path: str) -> dict:
        """Load YAML config"""
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Config load error: {e}")
            return {}

    def _init_buffer(self):
        """Initialize SQLite buffer for offline storage"""
        try:
            conn = sqlite3.connect(self.buffer_db)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS buffer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    attempts INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Buffer init error: {e}")

    def send(self, data: List[Dict]) -> bool:
        """
        Send data to cloud (works with old nettemp format)

        Args:
            data: List of dicts with keys: rom, type, value, name

        Returns:
            True if successful
        """
        if not self.enabled or not self.cloud_url or not self.api_key:
            return False

        # Transform old format to cloud format
        cloud_data = self._transform_data(data)

        # Try to send
        if self._send_to_cloud(cloud_data):
            # Success - try to flush buffer
            self._flush_buffer()
            return True
        else:
            # Failed - add to buffer
            self._add_to_buffer(cloud_data)
            return False

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
        # If the rom starts with device/group, strip it first
        if rom.startswith(self.device_id):
            rom = rom[len(self.device_id):]
        # Strip leading underscores that drivers commonly include
        rom = rom.lstrip('_')

        # DS18B20: 28-00000a1b2c
        if rom.startswith('28-'):
            return {'id': rom, 'type': '1wire'}

        # DHT: _dht22_temp_gpio_D4
        if 'dht' in rom.lower():
            if 'D' in rom:
                pin = rom.split('_D')[1] if '_D' in rom else '0'
                sensor = 'dht22' if 'dht22' in rom.lower() else 'dht11'
                return {'id': f'{sensor}-gpio{pin}', 'type': 'gpio'}

        # I2C: _i2c_76_temp
        if 'i2c' in rom.lower():
            parts = rom.split('_')
            for i, part in enumerate(parts):
                if part == 'i2c' and i + 1 < len(parts):
                    addr = parts[i + 1]
                    return {'id': f'i2c-0x{addr}', 'type': 'i2c'}

        # Fallback: use ROM as-is or hash
        if len(rom) > 20:
            hash_short = hashlib.md5(rom.encode()).hexdigest()[:8]
            return {'id': f'sensor-{hash_short}', 'type': 'unknown'}

        return {'id': rom or 'unknown', 'type': 'unknown'}

    def _send_to_cloud(self, data: Dict) -> bool:
        """Send data to cloud API"""
        for attempt in range(self.retry_attempts):
            try:
                # Include X-Readings-Count so server can account for batched readings
                headers = {'X-Readings-Count': str(len(data.get('readings', [])))}
                response = self.session.post(
                    f'{self.cloud_url}/api/v1/data',
                    json=data,
                    headers=headers,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    return True
                elif response.status_code == 401:
                    print("Cloud: Invalid API key")
                    return False
                elif response.status_code == 429:
                    # Rate limited
                    time.sleep(2 ** attempt)
                    continue
                else:
                    print(f"Cloud: Error {response.status_code}")

            except requests.exceptions.Timeout:
                if attempt < self.retry_attempts - 1:
                    time.sleep(1)
            except Exception as e:
                print(f"Cloud: {e}")
                break

        return False

    def _add_to_buffer(self, data: Dict):
        """Add failed data to local buffer"""
        try:
            conn = sqlite3.connect(self.buffer_db)
            conn.execute(
                'INSERT INTO buffer (data, timestamp) VALUES (?, ?)',
                (json.dumps(data), int(time.time()))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Buffer add error: {e}")

    def _flush_buffer(self):
        """Try to send buffered data"""
        try:
            conn = sqlite3.connect(self.buffer_db)
            cursor = conn.execute(
                'SELECT id, data FROM buffer WHERE attempts < 5 ORDER BY timestamp LIMIT 10'
            )
            rows = cursor.fetchall()

            for row_id, data_json in rows:
                data = json.loads(data_json)
                if self._send_to_cloud(data):
                    # Success - delete from buffer
                    conn.execute('DELETE FROM buffer WHERE id = ?', (row_id,))
                else:
                    # Failed - increment attempts
                    conn.execute(
                        'UPDATE buffer SET attempts = attempts + 1 WHERE id = ?',
                        (row_id,)
                    )

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Buffer flush error: {e}")

    def close(self):
        """Close session"""
        self.session.close()


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
            print("Cannot load config")
            return

        group = config.get('group', socket.gethostname())

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
                print(f"[Local] Data sent")
            except Exception as e:
                print(f"[Local] Cannot connect: {e}")

        # 2. Send to cloud
        if config.get('cloud_enabled'):
            try:
                if not self._cloud_client:
                    self._cloud_client = CloudClient(config_file)

                if self._cloud_client.send(self.data):
                    print(f"[Cloud] Data sent")
                else:
                    print(f"[Cloud] Buffered for retry")
            except Exception as e:
                print(f"[Cloud] Error: {e}")

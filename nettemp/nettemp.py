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
import urllib3

# Disable SSL warnings for local/docker servers
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from .paths import get_config_file, get_drivers_file
except Exception:
    # When executed with a cwd that points at the package directory (or as a script),
    # relative imports may fail. Fall back to absolute/top-level imports.
    try:
        from nettemp.paths import get_config_file, get_drivers_file  # type: ignore
    except Exception:  # pragma: no cover
        from paths import get_config_file, get_drivers_file  # type: ignore


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
                    # Get verify_ssl setting, default based on URL
                    url = server.get('url', '').rstrip('/')
                    verify_ssl = server.get('verify_ssl')
                    
                    # If verify_ssl not specified, use True (always verify by default)
                    if verify_ssl is None:
                        verify_ssl = True
                    
                    servers.append({
                        'url': url,
                        'api_key': server.get('api_key', ''),
                        'enabled': server.get('enabled', True),
                        'name': server.get('name', server.get('url', 'unnamed')),
                        'verify_ssl': verify_ssl,
                        'format': server.get('format', 'cloud')
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

    def _filter_servers_for_driver(self, driver_name: str = None) -> List[Dict]:
        """
        Filter cloud servers based on driver configuration.
        
        Returns servers that should receive data from this driver:
        - If driver has 'servers' list: only return servers with matching names
        - If driver has no 'servers' or empty list: return all enabled servers
        - If driver_name is None: return all enabled servers
        """
        # Return all enabled servers if no driver specified
        if not driver_name:
            return [s for s in self.cloud_servers if s.get('enabled', True)]
        
        # Load driver config to check for server filtering
        try:
            import yaml
            config_file = get_drivers_file()
            if config_file.exists():
                with open(config_file, 'r') as f:
                    drivers_config = yaml.safe_load(f) or {}
                    driver_cfg = drivers_config.get(driver_name, {})
                    target_server_names = driver_cfg.get('servers', [])
                    
                    # If driver has no 'servers' field or empty list, send to all enabled
                    if not target_server_names:
                        return [s for s in self.cloud_servers if s.get('enabled', True)]
                    
                    # Filter to only servers listed in driver config
                    filtered = []
                    for server in self.cloud_servers:
                        if not server.get('enabled', True):
                            continue
                        server_name = server.get('name', '')
                        if server_name in target_server_names:
                            filtered.append(server)
                    
                    if filtered:
                        logging.debug(f"[{driver_name}] Sending to servers: {[s.get('name') for s in filtered]}")
                    else:
                        logging.warning(f"[{driver_name}] No matching servers found for: {target_server_names}")
                    
                    return filtered
        except Exception as e:
            logging.warning(f"Failed to load driver config for filtering: {e}")
        
        # Fallback: return all enabled servers
        return [s for s in self.cloud_servers if s.get('enabled', True)]

    def send(self, data: List[Dict], driver_name: str = None) -> bool:
        """
        Send data to cloud servers (works with old nettemp format)
        
        Filters servers based on driver configuration:
        - If driver has 'servers' field: only send to those servers
        - If driver has no 'servers' field or empty list: send to all enabled servers

        Args:
            data: List of dicts with keys: rom, type, value, name
            driver_name: Name of the driver generating this data (for server filtering)

        Returns:
            True if sent successfully to at least one server
        """
        if not self.cloud_servers:
            return False

        # Transform old format to cloud format once (for servers that need it)
        cloud_data = self._transform_data(data)
        readings = cloud_data.get('readings', []) or []
        if not readings:
            return False

        # Track if we successfully sent to at least one server
        any_success = False

        # Filter servers based on driver configuration
        target_servers = self._filter_servers_for_driver(driver_name)

        # Send to each target server with appropriate format
        for server in target_servers:
            # Check if server needs legacy format
            server_format = server.get('format', 'cloud')
            if server_format == 'legacy':
                # Send raw data in old format
                server_success = self._send_to_server_legacy(data, server)
            else:
                # Send transformed cloud format
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

        logging.debug(f"[Cloud] Transforming {len(data)} readings from driver")
        for item in data:
            # Parse old ROM format
            sensor_info = self._parse_rom(item.get('rom', ''))
            
            # Always prepend device_id to sensor_id if not already present
            sensor_id = sensor_info['id']
            if self.device_id and not sensor_id.startswith(f'{self.device_id}-'):
                sensor_id = f'{self.device_id}-{sensor_id}'

            readings.append({
                'sensor_id': sensor_id,
                'sensor_type': item.get('type', ''),  # Send as-is, backend normalizes
                'value': float(item.get('value', 0)),
                'unit': item.get('unit', ''),  # Send unit if provided, backend fills if empty
                'timestamp': int(time.time()),
                'metadata': {
                    'name': item.get('name', ''),
                    'original_rom': item.get('rom', '')
                }
            })
            logging.debug(f"[Cloud]   - {sensor_id}: {item.get('value')} ({item.get('type')})")

        logging.info(f"[Cloud] Sending {len(readings)} reading(s) to cloud")
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

        # DS18B20: 28-00000a1b2c or 28_00000a1b2c (keep underscore format for cloud)
        if rom.startswith('28-') or rom.startswith('28_'):
            # Keep original format (underscore preferred for cloud API)
            if group:
                return {'id': f'{group}-{rom}', 'type': '1wire'}
            return {'id': rom, 'type': '1wire'}

        # LYWSD03MMC BLE: lywsd03mmc_A4C138DE459E_temp or lywsd03mmc_A4C138DE459E_humid
        if 'lywsd03mmc' in rom.lower():
            # Keep full sensor ID including _temp or _humid suffix for uniqueness
            # rom format: lywsd03mmc_A4C138DE459E_temp or lywsd03mmc_A4C138DE459E_humid
            sensor_id = rom  # Use the full rom as sensor_id to keep temp/humid separate
            if group:
                return {'id': f'{group}-{sensor_id}', 'type': 'ble'}
            return {'id': sensor_id, 'type': 'ble'}
        
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
                    # Get full measurement type suffix (everything after address: temp, acce_x, etc.)
                    suffix_parts = [p for p in parts[i + 2:] if p]  # Skip empty parts
                    suffix = '_'.join(suffix_parts) if suffix_parts else None
                    # If there's a token before 'i2c' that looks like a driver name, include it
                    driver = parts[i - 1] if i - 1 >= 0 and parts[i - 1] else None
                    
                    # Build sensor ID with suffix to differentiate multiple readings from same device
                    if driver and suffix:
                        if group:
                            return {'id': f'{group}-{driver.lower()}-i2c-0x{addr}-{suffix}', 'type': 'i2c'}
                        return {'id': f'{driver.lower()}-i2c-0x{addr}-{suffix}', 'type': 'i2c'}
                    elif driver:
                        if group:
                            return {'id': f'{group}-{driver.lower()}-i2c-0x{addr}', 'type': 'i2c'}
                        return {'id': f'{driver.lower()}-i2c-0x{addr}', 'type': 'i2c'}
                    elif suffix:
                        if group:
                            return {'id': f'{group}-i2c-0x{addr}-{suffix}', 'type': 'i2c'}
                        return {'id': f'i2c-0x{addr}-{suffix}', 'type': 'i2c'}
                    else:
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
        verify_ssl = server.get('verify_ssl', True)  # Use server's setting, default to True

        for attempt in range(self.retry_attempts):
            try:
                # Create session for this specific server with its API key
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'NettempCloud/1.0',
                    'X-Readings-Count': str(len(data.get('readings', [])))
                }
                
                readings_count = len(data.get('readings', []))
                logging.debug(f"[Cloud:{name}] POSTing {readings_count} readings to {url}/api/v1/data")
                
                response = requests.post(
                    f'{url}/api/v1/data',
                    json=data,
                    headers=headers,
                    timeout=self.timeout,
                    verify=verify_ssl
                )

                if response.status_code == 200:
                    logging.info(f"[Cloud:{name}] Successfully sent {readings_count} readings")
                    return True
                elif response.status_code == 207:
                    # 207 Multi-Status: partial success (some readings rejected)
                    try:
                        result = response.json()
                        accepted = result.get('accepted', 0)
                        rejected = result.get('rejected', 0)
                        logging.warning(f"[Cloud:{name}] Partial success: {accepted} accepted, {rejected} rejected (min/max limits)")
                    except Exception:
                        logging.warning(f"[Cloud:{name}] Partial success (some readings rejected)")
                    return True  # Don't buffer rejected readings
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

    def _send_to_server_legacy(self, data: List[Dict], server: Dict[str, str]) -> bool:
        """Send data to server using legacy format (raw array)"""
        url = server['url']
        api_key = server['api_key']
        name = server.get('name', url)
        verify_ssl = server.get('verify_ssl', True)

        # Add group to data for legacy format
        legacy_data = []
        for item in data:
            item_copy = item.copy()
            item_copy['group'] = self.device_id
            # Ensure rom includes group prefix
            rom_raw = item_copy.get('rom', '') or ''
            if not rom_raw.startswith(self.device_id):
                item_copy['rom'] = f"{self.device_id}_{rom_raw.lstrip('_')}"
            legacy_data.append(item_copy)

        for attempt in range(self.retry_attempts):
            try:
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                }
                
                response = requests.post(
                    url,  # Legacy format posts to root, not /api/v1/data
                    json=legacy_data,
                    headers=headers,
                    timeout=self.timeout,
                    verify=verify_ssl
                )

                if response.status_code in [200, 201]:
                    logging.info(f"[Legacy:{name}] Sent {len(data)} readings")
                    return True
                elif response.status_code == 401:
                    logging.error(f"[Legacy:{name}] Invalid API key")
                    return False
                elif response.status_code == 429:
                    logging.warning(f"[Legacy:{name}] Rate limited, retrying...")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    logging.error(f"[Legacy:{name}] Error {response.status_code}")

            except requests.exceptions.Timeout:
                logging.warning(f"[Legacy:{name}] Timeout (attempt {attempt + 1}/{self.retry_attempts})")
                if attempt < self.retry_attempts - 1:
                    time.sleep(1)
            except Exception as e:
                logging.error(f"[Legacy:{name}] Error: {e}")
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
        config_file = str(get_config_file())

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

import json
import logging
import threading
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs

from nettemp import insert2


class HTTPBridge:
    """Lightweight HTTP bridge that accepts local HTTP requests and forwards them to Nettemp Cloud."""

    def __init__(self, cloud_client, default_device_id: str, config: dict | None):
        self.cloud_client = cloud_client
        self.default_device_id = default_device_id or 'nettemp-client'
        cfg = config or {}
        self.enabled = bool(cfg.get('enabled', False))
        self.host = cfg.get('host', '0.0.0.0')
        self.port = int(cfg.get('port', 0))
        self.auth_token = cfg.get('auth_token')
        self.server: socketserver.ThreadingTCPServer | None = None
        self.thread: threading.Thread | None = None
        self.shutdown_event: threading.Event | None = None

    def start(self):
        if not (self.enabled and self.port):
            return

        bridge = self
        self.shutdown_event = threading.Event()

        class BridgeRequestHandler(http.server.BaseHTTPRequestHandler):
            def _check_auth(self) -> bool:
                if bridge.auth_token:
                    auth = self.headers.get('Authorization', '')
                    if auth != f'Bearer {bridge.auth_token}':
                        self.send_error(401, 'Unauthorized')
                        return False
                return True

            def _send_result(self, success: bool):
                if success:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'ok')
                else:
                    self.send_error(502, 'Failed to forward payload')

            def do_POST(self):
                if not self._check_auth():
                    return
                try:
                    length = int(self.headers.get('Content-Length', '0') or 0)
                except ValueError:
                    length = 0
                body = self.rfile.read(length) if length else b''
                try:
                    payload = json.loads(body.decode('utf-8') or '[]')
                except Exception:
                    self.send_error(400, 'Invalid JSON payload')
                    return
                success = bridge._handle_payload(payload)
                self._send_result(success)

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path.startswith('/generic_http'):
                    if not self._check_auth():
                        return
                    params = parse_qs(parsed.query)
                    success = bridge._handle_generic(params)
                    self._send_result(success)
                else:
                    self.send_error(404)

            def log_message(self, format, *args):
                logging.info('bridge: ' + format % args)

        class BridgeServer(socketserver.ThreadingTCPServer):
            allow_reuse_address = True

        try:
            self.server = BridgeServer((self.host, self.port), BridgeRequestHandler)
        except OSError as e:
            logging.error(f'Failed to start HTTP bridge on {self.host}:{self.port}: {e}')
            self.server = None
            return

        logging.info(f'HTTP bridge listening on {self.host}:{self.port}')

        def serve():
            assert self.server is not None
            while not self.shutdown_event.is_set():
                self.server.handle_request()

        self.thread = threading.Thread(target=serve, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.server:
            return
        logging.info('Stopping HTTP bridge')
        try:
            if self.shutdown_event:
                self.shutdown_event.set()
            self.server.server_close()
        except Exception:
            pass
        self.server = None

    def _handle_payload(self, payload) -> bool:
        try:
            if isinstance(payload, list):
                insert2(payload).request()
                return True
            if isinstance(payload, dict):
                if 'readings' in payload:
                    data = payload.copy()
                    if not data.get('device_id'):
                        data['device_id'] = self.default_device_id
                    if hasattr(self.cloud_client, 'send_payload'):
                        return self.cloud_client.send_payload(data)
                    return False
                if 'rom' in payload:
                    insert2([payload]).request()
                    return True
        except Exception as e:
            logging.error(f'Bridge payload forward failed: {e}')
        return False

    def _handle_generic(self, params: dict[str, list[str]]) -> bool:
        try:
            sysname = params.get('name', [''])[0] or self.default_device_id
            task = params.get('task', params.get('taskname', ['']))[0]
            valuename = params.get('valuename', ['value'])[0]
            value_raw = params.get('value', ['0'])[0]
            unit = params.get('unit', [''])[0]
            value = float(value_raw)

            rom_parts = [sysname]
            if task:
                rom_parts.append(task)
            rom_parts.append(valuename)
            rom = '_'.join([p for p in rom_parts if p])

            payload = [{
                'rom': rom,
                'type': valuename,
                'value': value,
                'unit': unit,
                'name': f'{task}/{valuename}' if task else valuename
            }]
            insert2(payload).request()
            return True
        except Exception as e:
            logging.error(f'Bridge generic payload failed: {e}')
        return False

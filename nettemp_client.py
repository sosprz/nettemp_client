#!/usr/bin/env python3
"""
Nettemp client — automatic foreground/background behavior (no switches required)

Behavior:
- If you run the script interactively and a background instance is running, the
  foreground run will automatically stop the background instance, run in the
  terminal for debugging, and when it exits it will re-spawn a detached
  background instance so the client keeps running.
- Background mode is implemented by launching the same script with the
  environment variable NETTEMP_CLIENT_BG=1 (this is internal; you don't need
  to set it yourself).
"""
import sys
import time
import logging
import os
import signal
import argparse
import subprocess
import http.server
import socketserver
import threading
import json
from urllib.parse import urlparse, parse_qs
from pathlib import Path

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:
    BackgroundScheduler = None

sys.path.insert(0, str(Path(__file__).parent))

from nettemp import CloudClient, insert2
from driver_loader import DriverLoader

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

PIDFILE = Path(__file__).parent / '.nettemp_client.pid'


def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def read_pidfile() -> int | None:
    try:
        if PIDFILE.exists():
            return int(PIDFILE.read_text().strip())
    except Exception:
        return None
    return None


def write_pidfile(pid: int):
    try:
        PIDFILE.write_text(str(pid))
    except Exception as e:
        logging.warning(f'Could not write pidfile: {e}')


def remove_pidfile():
    try:
        if PIDFILE.exists():
            PIDFILE.unlink()
    except Exception as e:
        logging.debug(f'Failed to remove pidfile: {e}')


class NettempClient:
    def __init__(self, config_file='config.conf', drivers_config='drivers_config.yaml', bg_mode: bool = False):
        if BackgroundScheduler is None:
            raise RuntimeError('apscheduler is required: pip install apscheduler')
        self.loader = DriverLoader(config_file=drivers_config)
        self.cloud_client = CloudClient(config_file)
        self.config_file = config_file
        self.bg_mode = bg_mode
        self.scheduler = BackgroundScheduler()
        bridge_cfg = self.cloud_client.config.get('http_bridge') or {}
        self.bridge_enabled = bool(bridge_cfg.get('enabled', False))
        self.bridge_host = bridge_cfg.get('host', '0.0.0.0')
        self.bridge_port = int(bridge_cfg.get('port', 0))
        self.bridge_token = bridge_cfg.get('auth_token')
        self.bridge_thread: threading.Thread | None = None
        self.bridge_server: socketserver.TCPServer | None = None
        self.bridge_shutdown_event = threading.Event()

    class _HTTPBridgeHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.server.process_json_payload(self)

        def do_GET(self):
            if self.path.startswith('/generic_http'):
                self.server.process_generic_http(self)
            else:
                self.send_error(404)

        def log_message(self, format, *args):
            logging.info("bridge: " + format % args)

    class _HTTPBridgeServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

        def __init__(self, server_address, handler_cls, token, json_callback, generic_callback, shutdown_event):
            super().__init__(server_address, handler_cls)
            self.auth_token = token
            self.json_callback = json_callback
            self.generic_callback = generic_callback
            self.shutdown_event = shutdown_event

        def _check_auth(self, handler):
            if self.auth_token:
                auth = handler.headers.get('Authorization', '')
                if auth != f'Bearer {self.auth_token}':
                    handler.send_error(401, 'Unauthorized')
                    return False
            return True

        def process_json_payload(self, handler):
            if not self._check_auth(handler):
                return
            try:
                length = int(handler.headers.get('Content-Length', 0))
            except ValueError:
                length = 0
            body = handler.rfile.read(length) if length else b''
            try:
                payload = json.loads(body.decode('utf-8') or '[]')
            except Exception:
                handler.send_error(400, 'Invalid JSON payload')
                return

            try:
                success = self.json_callback(payload)
                if success:
                    handler.send_response(200)
                    handler.end_headers()
                    handler.wfile.write(b'ok')
                else:
                    handler.send_error(502, 'Failed to forward payload')
            except Exception as e:
                logging.error(f'Bridge error: {e}')
                handler.send_error(500, 'Internal error')

        def process_generic_http(self, handler):
            if not self.generic_callback:
                handler.send_error(404)
                return
            if not self._check_auth(handler):
                return
            try:
                query = parse_qs(urlparse(handler.path).query)
                success = self.generic_callback(query)
                if success:
                    handler.send_response(200)
                    handler.end_headers()
                    handler.wfile.write(b'ok')
                else:
                    handler.send_error(502, 'Failed to process payload')
            except Exception as e:
                logging.error(f'Bridge error: {e}')
                handler.send_error(500, 'Internal error')

        def serve_forever(self, poll_interval=0.5):
            while not self.shutdown_event.is_set():
                self.handle_request()

    def _forward_http_payload(self, payload):
        try:
            if isinstance(payload, list):
                insert2(payload).request()
                return True
            if isinstance(payload, dict):
                if 'readings' in payload:
                    data = payload.copy()
                    if not data.get('device_id'):
                        data['device_id'] = self.cloud_client.device_id
                    if self.cloud_client.send_payload(data):
                        return True
                    return False
                if 'rom' in payload:
                    insert2([payload]).request()
                    return True
        except Exception as e:
            logging.error(f'Forward payload failed: {e}')
        return False

    def _forward_generic_http(self, params):
        try:
            sysname = params.get('name', [''])[0] or self.cloud_client.device_id or 'nettemp-client'
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
            logging.error(f'Failed to process generic HTTP payload: {e}')
        return False

    def _start_http_bridge(self):
        if not (self.bridge_enabled and self.bridge_port):
            return
        try:
            shutdown_event = threading.Event()
            server = self._HTTPBridgeServer(
                (self.bridge_host, self.bridge_port),
                self._HTTPBridgeHandler,
                self.bridge_token,
                self._forward_http_payload,
                self._forward_generic_http,
                shutdown_event
            )
            self.bridge_shutdown_event = shutdown_event
            self.bridge_server = server

            def run_server():
                logging.info(f'HTTP bridge listening on {self.bridge_host}:{self.bridge_port}')
                try:
                    server.serve_forever()
                except Exception as e:
                    logging.error(f'HTTP bridge error: {e}')

            self.bridge_thread = threading.Thread(target=run_server, daemon=True)
            self.bridge_thread.start()
        except Exception as e:
            logging.error(f'Failed to start HTTP bridge: {e}')

    def _stop_http_bridge(self):
        if self.bridge_server:
            logging.info('Stopping HTTP bridge')
            try:
                if self.bridge_shutdown_event:
                    self.bridge_shutdown_event.set()
                self.bridge_server.server_close()
            except Exception:
                pass
            self.bridge_server = None

    def read_and_send(self, driver_name, driver_config):
        logging.info(f'Reading: {driver_name}')
        readings = self.loader.run_driver(driver_name, driver_config)
        if not readings:
            logging.warning(f'No readings from {driver_name}')
            return
        try:
            sender = insert2(readings)
            sender.request()
            logging.info(f'Sent {len(readings)} readings for {driver_name}')
        except Exception as e:
            logging.error(f'Failed to send {driver_name}: {e}')

    def schedule_drivers(self):
        enabled = self.loader.get_enabled_drivers()
        for name, cfg in enabled:
            interval = int(cfg.get('read_in_sec', 60))
            if self.scheduler.get_job(name):
                continue
            self.scheduler.add_job(self.read_and_send, 'interval', seconds=interval, args=[name, cfg], id=name)
            logging.info(f'Scheduled {name} every {interval}s')

    def _reschedule_drivers(self):
        """Reload driver config and reschedule jobs to match enabled drivers."""
        # reload config from disk
        new_config = self.loader.load_config()
        self.loader.config = new_config

        # remove all existing driver jobs
        for job in list(self.scheduler.get_jobs()):
            try:
                self.scheduler.remove_job(job.id)
                logging.info(f'Removed job: {job.id}')
            except Exception:
                logging.debug(f'Failed to remove job: {job.id}')

        # schedule according to new config
        enabled = self.loader.load_drivers_from_config(new_config)
        for name, cfg, interval in enabled:
            try:
                self.scheduler.add_job(self.read_and_send, 'interval', seconds=int(interval), args=[name, cfg], id=name)
                logging.info(f'Scheduled {name} every {int(interval)}s')
            except Exception as e:
                logging.error(f'Failed to schedule {name}: {e}')

    def _restart_process(self):
        """Restart the current process (exec into new instance)."""
        try:
            python = sys.executable
            os.execv(python, [python] + sys.argv)
        except Exception:
            logging.exception('Failed to restart process')

    def start(self):
        self.schedule_drivers()
        self.scheduler.start()
        logging.info('Runner started')

        # track drivers_config.yaml mtime for reloads
        drivers_mtime = None
        try:
            if self.loader.config_file.exists():
                drivers_mtime = self.loader.config_file.stat().st_mtime
        except Exception:
            drivers_mtime = None

        # track config.conf mtime so we can restart to apply changes
        conf_path = Path(self.config_file)
        conf_mtime = None
        try:
            if conf_path.exists():
                conf_mtime = conf_path.stat().st_mtime
        except Exception:
            conf_mtime = None

        if self.bridge_enabled and self.bridge_port:
            self._start_http_bridge()

        try:
            while True:
                time.sleep(1)

                # poll drivers_config.yaml for changes and reschedule if changed
                try:
                    if self.loader.config_file.exists():
                        new_m = self.loader.config_file.stat().st_mtime
                        if drivers_mtime is None or new_m > drivers_mtime:
                            drivers_mtime = new_m
                            logging.info('Detected change in drivers_config.yaml — reloading and rescheduling drivers')
                            self._reschedule_drivers()
                except Exception as e:
                    logging.error(f'Error watching drivers config: {e}')

                # watch config.conf for changes and restart automatically (no prompt)
                try:
                    if conf_path.exists():
                        newc = conf_path.stat().st_mtime
                        if conf_mtime is None:
                            conf_mtime = newc
                        elif newc > conf_mtime:
                            conf_mtime = newc
                            logging.info('Detected change in config.conf — restarting to apply changes')
                            # restart process to pick up new config
                            self._restart_process()
                except Exception as e:
                    logging.error(f'Error watching config.conf: {e}')
        except KeyboardInterrupt:
            logging.info('Stopping runner')
            self.scheduler.shutdown()
            self._stop_http_bridge()


def main():
    # Keep an optional hidden flag for compatibility only; normal behavior is automatic
    parser = argparse.ArgumentParser()
    parser.add_argument('--autorespawn', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()

    # Determine background mode automatically:
    # - If started without a controlling TTY (e.g. from cron/@reboot or with &), treat as background.
    # - If started interactively (tty present), treat as foreground.
    bg_mode = not os.isatty(0)

    # Background mode: run detached loop and restart on crash. This covers cron @reboot
    # entries (they run without a TTY) and manual starts with & where stdin is not a TTY.
    if bg_mode:
        write_pidfile(os.getpid())
        try:
            while True:
                try:
                    client = NettempClient(
                        config_file='config.conf',
                        drivers_config='drivers_config.yaml',
                        bg_mode=True
                    )
                    client.start()
                    break
                except KeyboardInterrupt:
                    break
                except Exception:
                    logging.exception('Background client crashed, restarting in 2s')
                    time.sleep(2)
        finally:
            remove_pidfile()
        return

    # Foreground interactive run: stop any background instance and remember to restart it after
    restart_background_after = False
    existing = read_pidfile()
    if existing and is_process_running(existing):
        if os.isatty(0):
            logging.info(f'Detected background instance (pid {existing}) — stopping it to run locally')
            try:
                os.kill(existing, signal.SIGTERM)
                restart_background_after = True
                time.sleep(1)
            except Exception:
                logging.exception(f'Failed to stop background instance {existing} — aborting')
                return
        else:
            logging.error('Client already running in background; aborting')
            return

    # Run in foreground for debugging
    write_pidfile(os.getpid())
    try:
        client = NettempClient(
            config_file='config.conf',
            drivers_config='drivers_config.yaml',
            bg_mode=False
        )
        client.start()
    finally:
        remove_pidfile()

        # After local debug session, restore background if we stopped one earlier
        if restart_background_after:
            env = os.environ.copy()
            env['NETTEMP_CLIENT_BG'] = '1'
            with open(os.devnull, 'wb') as devnull:
                subprocess.Popen([sys.executable, __file__], stdout=devnull, stderr=devnull, start_new_session=True, env=env)
            logging.info('Restored background nettemp client')


if __name__ == '__main__':
    main()

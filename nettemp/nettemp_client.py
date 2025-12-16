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
import os
from pathlib import Path

# Allow running as a script (python nettemp_client.py) by fixing package context
if __package__ in (None, ''):
    pkg_dir = Path(__file__).parent
    sys.path.append(str(pkg_dir.parent))  # add parent so "nettemp" is importable
    __package__ = 'nettemp'

# Auto-activate venv if not already in it
script_dir = Path(__file__).parent.resolve()
venv_path = script_dir / 'venv'
venv_python = venv_path / 'bin' / 'python3'

# Check if we're NOT in venv and venv exists
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    if venv_python.exists():
        # Restart with venv python
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)

import time
import logging
import signal
import argparse
import subprocess

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:
    BackgroundScheduler = None

# Change to script directory to ensure relative paths work correctly
os.chdir(script_dir)

from .nettemp import CloudClient, insert2
from .driver_loader import DriverLoader
from .bridge import HTTPBridge
from .mqtt.mqtt import MQTTBridge
from .mqtt.theengs_gateway_manager import TheengsGatewayManager

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
# Quiet down APScheduler noise (job executed/run messages)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

PIDFILE = Path(__file__).parent / '.nettemp_client.pid'

# BLE drivers that need separate scheduling (to avoid blocking other sensors)
BLE_DRIVERS = ['lywsd03mmc']


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
        self.scheduler = BackgroundScheduler()  # For non-BLE sensors
        self.ble_scheduler = BackgroundScheduler()  # Separate scheduler for BLE sensors
        self.bridge = HTTPBridge(
            self.cloud_client,
            self.cloud_client.device_id,
            self.cloud_client.config.get('http_bridge')
        )
        self.mqtt = MQTTBridge(
            self.cloud_client,
            self.cloud_client.device_id,
            self.cloud_client.config.get('mqtt')
        )
        self.theengs_gateway = TheengsGatewayManager(
            self.cloud_client.config.get('theengs_gateway')
        )


    def read_and_send(self, driver_name, driver_config):
        readings = self.loader.run_driver(driver_name, driver_config)
        if not readings:
            logging.warning(f'No readings from {driver_name}')
            return

        # Single-line log with driver name and values
        try:
            summary = "; ".join(
                f"{r.get('name', r.get('rom', 'unknown'))}={r.get('value')}"
                for r in readings
            )
        except Exception:
            summary = str(readings)
        logging.info(f"Reading: {driver_name} {summary}")

        try:
            # Send readings with driver_name for per-driver server filtering
            success = self.cloud_client.send(readings, driver_name=driver_name)
            if not success:
                logging.warning(f'Failed to send {driver_name} to any server')
            
            # Publish to MQTT if enabled
            if self.mqtt and self.mqtt.enabled and self.mqtt.mode_publisher:
                self.mqtt.publish_readings(readings, self.cloud_client.device_id)
        except Exception as e:
            logging.error(f'Failed to send {driver_name}: {e}')

    def schedule_drivers(self):
        enabled = self.loader.get_enabled_drivers()
        for name, cfg in enabled:
            interval = int(cfg.get('read_in_sec', 60))
            
            # Determine which scheduler to use
            is_ble = name in BLE_DRIVERS
            scheduler = self.ble_scheduler if is_ble else self.scheduler
            
            if scheduler.get_job(name):
                continue
            
            # Send data immediately on start (skip for BLE to avoid initial connection issues)
            if not is_ble:
                try:
                    self.read_and_send(name, cfg)
                except Exception as e:
                    logging.error(f'Initial read failed for {name}: {e}')
            else:
                logging.info(f'BLE sensor {name} will read on first scheduled interval (avoiding initial connection issues)')
            
            # Then schedule regular intervals
            scheduler.add_job(self.read_and_send, 'interval', seconds=interval, args=[name, cfg], id=name)
            sensor_type = 'BLE sensor' if is_ble else 'sensor'
            logging.info(f'Scheduled {sensor_type} {name} every {interval}s')

    def _reschedule_drivers(self):
        """Reload driver config and reschedule jobs to match enabled drivers."""
        # reload config from disk
        new_config = self.loader.load_config()
        self.loader.config = new_config

        # remove all existing driver jobs from both schedulers
        for job in list(self.scheduler.get_jobs()):
            try:
                self.scheduler.remove_job(job.id)
                logging.info(f'Removed job: {job.id}')
            except Exception:
                logging.debug(f'Failed to remove job: {job.id}')
        
        for job in list(self.ble_scheduler.get_jobs()):
            try:
                self.ble_scheduler.remove_job(job.id)
                logging.info(f'Removed BLE job: {job.id}')
            except Exception:
                logging.debug(f'Failed to remove BLE job: {job.id}')

        # schedule according to new config
        enabled = self.loader.load_drivers_from_config(new_config)
        for name, cfg, interval in enabled:
            try:
                is_ble = name in BLE_DRIVERS
                scheduler = self.ble_scheduler if is_ble else self.scheduler
                
                # Send data immediately when reloading (skip BLE)
                if not is_ble:
                    try:
                        self.read_and_send(name, cfg)
                    except Exception as e:
                        logging.error(f'Initial read failed for {name}: {e}')
                
                scheduler.add_job(self.read_and_send, 'interval', seconds=int(interval), args=[name, cfg], id=name)
                sensor_type = 'BLE sensor' if is_ble else 'sensor'
                logging.info(f'Scheduled {sensor_type} {name} every {int(interval)}s')
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
        self.ble_scheduler.start()
        logging.info('Runner started (including separate BLE scheduler)')

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

        if self.bridge:
            self.bridge.start()
        
        if self.mqtt:
            self.mqtt.start()
        
        if self.theengs_gateway:
            self.theengs_gateway.start()

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
            self.ble_scheduler.shutdown()
            if self.bridge:
                self.bridge.stop()
            if self.mqtt:
                self.mqtt.stop()
            if self.theengs_gateway:
                self.theengs_gateway.stop()
    
    def stop(self):
        """Stop the schedulers and bridge"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
            if self.ble_scheduler.running:
                self.ble_scheduler.shutdown(wait=False)
            if self.bridge:
                self.bridge.stop()
            if self.mqtt:
                self.mqtt.stop()
            if self.theengs_gateway:
                self.theengs_gateway.stop()
        except Exception as e:
            logging.error(f'Error during shutdown: {e}')


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
            print(f'\n⚠️  Background instance detected (PID {existing})')
            print('If you stop this foreground session, the background instance will restart automatically.')
            print('This ensures continuous data collection.\n')
            
            try:
                response = input('Stop background and run in foreground for debugging? [Y/n]: ').strip().lower()
                if response and response not in ['y', 'yes']:
                    logging.info('Keeping background instance running')
                    return
            except (KeyboardInterrupt, EOFError):
                logging.info('\nCancelled — keeping background instance running')
                return
            
            logging.info(f'Stopping background instance (PID {existing})')
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
    client = None
    try:
        client = NettempClient(
            config_file='config.conf',
            drivers_config='drivers_config.yaml',
            bg_mode=False
        )
        client.start()
    except KeyboardInterrupt:
        logging.info('\nReceived interrupt signal')
        if client:
            client.stop()
    finally:
        remove_pidfile()

        # After local debug session, ask about restarting background
        if restart_background_after and os.isatty(0):
            try:
                print('\n' + '='*60)
                response = input('Restart background process? [Y/n]: ').strip().lower()
                if response and response not in ['y', 'yes']:
                    logging.info('Background process NOT restarted — no data collection will occur')
                    return
            except (KeyboardInterrupt, EOFError):
                logging.info('\nNo response — restarting background process automatically')
            
            env = os.environ.copy()
            env['NETTEMP_CLIENT_BG'] = '1'
            with open(os.devnull, 'wb') as devnull:
                subprocess.Popen([sys.executable, __file__], stdout=devnull, stderr=devnull, start_new_session=True, env=env)
            logging.info('✓ Background process restarted — data collection continues')
        elif restart_background_after:
            # Non-interactive: always restart
            env = os.environ.copy()
            env['NETTEMP_CLIENT_BG'] = '1'
            with open(os.devnull, 'wb') as devnull:
                subprocess.Popen([sys.executable, __file__], stdout=devnull, stderr=devnull, start_new_session=True, env=env)
            logging.info('Restored background nettemp client')


if __name__ == '__main__':
    main()

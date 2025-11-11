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
                    client = NettempClient(config_file='config.conf', drivers_config='drivers_config.yaml', bg_mode=True)
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
        client = NettempClient(config_file='config.conf', drivers_config='drivers_config.yaml', bg_mode=False)
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

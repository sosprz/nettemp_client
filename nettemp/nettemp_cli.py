"""
Lightweight CLI dispatcher for Nettemp.

Usage:
  nettemp config              # launch configurator (interactive)
  nettemp client              # run client (foreground/background auto as in nettemp_client)
  nettemp client start        # start background client if not running
  nettemp client stop         # stop background client
  nettemp client restart      # stop then start background client
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

from .nettemp_client import (
    main as client_main,
    read_pidfile,
    is_process_running,
    PIDFILE,
)
from .nettemp_config import main as config_main


def _start_background() -> int:
    pid = read_pidfile()
    if pid and is_process_running(pid):
        print(f"Nettemp client already running (PID {pid})")
        return 0

    env = os.environ.copy()
    env["NETTEMP_CLIENT_BG"] = "1"
    with open(os.devnull, "wb") as devnull:
        subprocess.Popen(
            [sys.executable, "-m", "nettemp_client"],
            stdin=devnull,
            stdout=devnull,
            stderr=devnull,
            start_new_session=True,
            env=env,
        )
    print("Started Nettemp client in background")
    return 0


def _stop_background() -> int:
    pid = read_pidfile()
    if not pid:
        print("No Nettemp client PID file found — nothing to stop")
        return 0
    if not is_process_running(pid):
        print(f"Stale PID file {PIDFILE}; removing")
        try:
            PIDFILE.unlink(missing_ok=True)
        except Exception:
            pass
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.5)
        print(f"Stopped Nettemp client (PID {pid})")
    except Exception as e:
        print(f"Failed to stop Nettemp client (PID {pid}): {e}")
        return 1
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    cmd = sys.argv[1].lower()
    if cmd == "config":
        return config_main() or 0

    if cmd == "client":
        if len(sys.argv) == 2:
            return client_main() or 0
        sub = sys.argv[2].lower()
        if sub == "start":
            return _start_background()
        if sub == "stop":
            return _stop_background()
        if sub == "restart":
            code = _stop_background()
            if code != 0:
                return code
            return _start_background()
        # Fallback: run client_main with original args beyond "client"
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        return client_main() or 0

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())

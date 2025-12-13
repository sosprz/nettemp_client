"""
Theengs Gateway Manager
Manages TheengsGateway BLE to MQTT bridge as a subprocess
"""

import subprocess
import logging
import json
import signal
import time
from pathlib import Path
from typing import Optional, Dict, Any


class TheengsGatewayManager:
    """Manage TheengsGateway process"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Theengs Gateway manager
        
        Args:
            config: Theengs Gateway configuration dict from config.conf
        """
        self.config = config or {}
        self.enabled = bool(self.config.get('enabled', False))
        self.process: Optional[subprocess.Popen] = None
        # Config file goes in parent directory (client root)
        self.config_file = Path(__file__).parent.parent / 'theengs_gateway_config.json'
        
        # Determine TheengsGateway command (venv or system) - look in parent directory
        script_dir = Path(__file__).parent.parent.resolve()
        venv_theengs = script_dir / 'venv' / 'bin' / 'TheengsGateway'
        
        if venv_theengs.exists():
            self.theengs_cmd = str(venv_theengs)
        else:
            self.theengs_cmd = 'TheengsGateway'
        
        if not self.enabled:
            logging.info('Theengs Gateway disabled in config')
            return
        
        # Check if TheengsGateway is installed
        try:
            # Try --version first
            result = subprocess.run([self.theengs_cmd, '--version'], 
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logging.info(f'Found TheengsGateway: {result.stdout.strip()} ({self.theengs_cmd})')
            else:
                # --version might not be supported, try --help or just check if file exists and is executable
                if venv_theengs.exists() and venv_theengs.is_file():
                    import stat
                    file_stat = venv_theengs.stat()
                    is_executable = bool(file_stat.st_mode & stat.S_IXUSR)
                    if is_executable:
                        logging.info(f'Found TheengsGateway at {self.theengs_cmd} (--version not supported)')
                    else:
                        logging.warning(f'TheengsGateway found but not executable: {self.theengs_cmd}')
                        logging.warning('Try: chmod +x {self.theengs_cmd}')
                        self.enabled = False
                else:
                    logging.warning('═' * 70)
                    logging.warning(f'TheengsGateway NOT FOUND at {self.theengs_cmd}')
                    logging.warning('Install with: pip install TheengsGateway')
                    logging.warning('Or in venv: ./venv/bin/pip install TheengsGateway')
                    logging.warning('═' * 70)
                    self.enabled = False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logging.warning('═' * 70)
            logging.warning(f'TheengsGateway NOT FOUND at {self.theengs_cmd}')
            logging.warning(f'Error: {e}')
            logging.warning('Install with: pip install TheengsGateway')
            logging.warning('Or in venv: ./venv/bin/pip install TheengsGateway')
            logging.warning('═' * 70)
            self.enabled = False
    
    def _create_config_file(self):
        """Create TheengsGateway JSON config file from config.conf settings"""
        try:
            gateway_config = {
                "host": self.config.get('mqtt_host', '127.0.0.1'),
                "port": int(self.config.get('mqtt_port', 1883)),
                "user": self.config.get('mqtt_user', ''),
                "pass": self.config.get('mqtt_pass', ''),
                "adapter": self.config.get('adapter', 'hci0'),
                "ble": int(self.config.get('ble', 1)),
                "ble_scan_time": int(self.config.get('ble_scan_time', 10)),
                "ble_time_between_scans": int(self.config.get('ble_time_between_scans', 30)),
                "scanning_mode": self.config.get('scanning_mode', 'passive'),
                "publish_topic": self.config.get('publish_topic', 'home/TheengsGateway/BTtoMQTT'),
                "subscribe_topic": self.config.get('subscribe_topic', 'home/+/BTtoMQTT/undecoded'),
                "publish_all": int(self.config.get('publish_all', 1)),
                "log_level": self.config.get('log_level', 'INFO')
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(gateway_config, f, indent=2)
            
            logging.info(f'Created Theengs Gateway config: {self.config_file}')
            return True
            
        except Exception as e:
            logging.error(f'Failed to create Theengs Gateway config: {e}')
            return False
    
    def start(self):
        """Start TheengsGateway as subprocess"""
        if not self.enabled:
            return
        
        if self.process and self.process.poll() is None:
            logging.info('Theengs Gateway already running')
            return
        
        # Create config file
        if not self._create_config_file():
            logging.error('Cannot start Theengs Gateway - config file creation failed')
            return
        
        try:
            # Start TheengsGateway
            logging.info(f'Starting Theengs Gateway with {self.theengs_cmd}...')
            self.process = subprocess.Popen(
                [self.theengs_cmd, '-c', str(self.config_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None  # Create process group
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if it's still running
            if self.process.poll() is None:
                logging.info(f'✓ Theengs Gateway started (PID: {self.process.pid})')
                logging.info(f'  Config: {self.config_file}')
                logging.info(f'  Command: {self.theengs_cmd} -c {self.config_file}')
            else:
                stdout, stderr = self.process.communicate(timeout=1)
                logging.error('═' * 70)
                logging.error('Theengs Gateway FAILED TO START')
                logging.error('═' * 70)
                logging.error(f'Command: {self.theengs_cmd} -c {self.config_file}')
                if stdout and stdout.strip():
                    logging.error(f'STDOUT:\n{stdout}')
                if stderr and stderr.strip():
                    logging.error(f'STDERR:\n{stderr}')
                logging.error('Check if TheengsGateway is properly installed:')
                logging.error(f'  pip list | grep -i theengs')
                logging.error('═' * 70)
                self.process = None
                
        except Exception as e:
            logging.error(f'Failed to start Theengs Gateway: {e}')
            self.process = None
    
    def stop(self):
        """Stop TheengsGateway subprocess"""
        if not self.process:
            return
        
        try:
            logging.info('Stopping Theengs Gateway...')
            
            # Try graceful shutdown first
            self.process.terminate()
            
            # Wait up to 5 seconds for graceful shutdown
            try:
                self.process.wait(timeout=5)
                logging.info('✓ Theengs Gateway stopped gracefully')
            except subprocess.TimeoutExpired:
                # Force kill if still running
                logging.warning('Theengs Gateway did not stop gracefully, forcing...')
                self.process.kill()
                self.process.wait()
                logging.info('✓ Theengs Gateway stopped (forced)')
            
            self.process = None
            
        except Exception as e:
            logging.error(f'Error stopping Theengs Gateway: {e}')
    
    def is_running(self) -> bool:
        """Check if TheengsGateway is running"""
        if not self.process:
            return False
        return self.process.poll() is None
    
    def restart(self):
        """Restart TheengsGateway"""
        self.stop()
        time.sleep(1)
        self.start()


import os  # Import at the end to avoid circular import issues

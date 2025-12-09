#!/usr/bin/env python3
"""
Nettemp Client - Interactive Configuration Menu

This interactive menu helps you:
- Configure server settings (nettemp.pl or custom IP)
- Enable/disable sensor drivers
- Discover I2C and 1-Wire devices
- View live sensor readings
- Test configuration before saving

Usage:
    python3 nettemp_config_menu.py
    
    Or with venv auto-activation:
    ./nettemp_config_menu.py
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

def check_and_setup_environment():
    """Auto-check and install dependencies if needed"""
    base_path = Path(__file__).parent
    venv_path = base_path / 'venv'
    requirements_file = base_path / 'requirements.txt'
    
    print("🔍 Checking environment...")
    
    # Check if Python 3 is available
    try:
        result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
        print(f"✓ Python found: {result.stdout.strip()}")
    except FileNotFoundError:
        print("✗ Python 3 not found!")
        print("Installing Python 3...")
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', '-y', 'install', 'python3', 'python3-pip', 'python3-venv'], check=True)
            print("✓ Python 3 installed")
        except Exception as e:
            print(f"✗ Failed to install Python 3: {e}")
            sys.exit(1)
    
    # Check/create virtual environment
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        try:
            subprocess.run(['python3', '-m', 'venv', str(venv_path)], check=True)
            print("✓ Virtual environment created")
        except Exception as e:
            print(f"✗ Failed to create venv: {e}")
            sys.exit(1)
    else:
        print("✓ Virtual environment exists")
    
    # Check if we're in venv, if not restart with venv python
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        venv_python = venv_path / 'bin' / 'python3'
        if venv_python.exists():
            print("🔄 Activating virtual environment...")
            os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    
    # Check/install requirements
    if requirements_file.exists():
        print("📦 Checking Python packages...")
        try:
            # Try importing key packages
            import yaml
            import tty
            import termios
            print("✓ Core packages installed")
            
            # Check for optional sensor packages
            missing_sensor_packages = []
            try:
                import adafruit_ads1x15
            except ImportError:
                missing_sensor_packages.append('adafruit-circuitpython-ads1x15')
            
            if missing_sensor_packages:
                print(f"ℹ Optional sensor packages not installed: {', '.join(missing_sensor_packages)}")
                print("  (Install if using capacitive soil moisture sensor with ADS1115 ADC)")
        except ImportError:
            print("Installing required packages...")
            pip_path = venv_path / 'bin' / 'pip3'
            try:
                subprocess.run([str(pip_path), 'install', '-r', str(requirements_file)], check=True)
                print("✓ Packages installed")
                print("🔄 Restarting with new packages...")
                # Restart to pick up newly installed packages
                venv_python = venv_path / 'bin' / 'python3'
                os.execv(str(venv_python), [str(venv_python)] + sys.argv)
            except Exception as e:
                print(f"⚠ Warning: Failed to install packages: {e}")
                print("You may need to run: pip3 install -r requirements.txt")
    
    # Check system tools
    missing_tools = []
    
    # Check cron
    try:
        subprocess.run(['crontab', '-l'], capture_output=True, check=False)
        print("✓ Cron installed")
    except FileNotFoundError:
        print("⚠ Cron not found")
        missing_tools.append('cron')
    
    # Check I2C tools
    try:
        subprocess.run(['i2cdetect', '-V'], capture_output=True, check=False)
        print("✓ I2C tools installed")
    except FileNotFoundError:
        print("⚠ I2C tools not found")
        missing_tools.append('i2c-tools')
    
    # Check lm-sensors
    try:
        subprocess.run(['sensors', '-v'], capture_output=True, check=False)
        print("✓ lm-sensors installed")
    except FileNotFoundError:
        print("⚠ lm-sensors not found")
        missing_tools.append('lm-sensors')
    
    # Offer to install missing tools
    if missing_tools:
        print(f"\n⚠ Missing system tools: {', '.join(missing_tools)}")
        install = input("Install missing tools? (y/n) [y]: ").strip().lower()
        if install in ['', 'y', 'yes']:
            try:
                print("Installing system packages...")
                subprocess.run(['sudo', 'apt-get', 'update'], check=True)
                subprocess.run(['sudo', 'apt-get', '-y', 'install'] + missing_tools, check=True)
                print("✓ System tools installed")
            except Exception as e:
                print(f"⚠ Warning: Failed to install some tools: {e}")
                print(f"  Install manually with: sudo apt-get install {' '.join(missing_tools)}")
    
    # Check if user is in i2c group (needed for I2C sensor access)
    try:
        import grp
        import pwd
        username = pwd.getpwuid(os.getuid()).pw_name
        i2c_group = grp.getgrnam('i2c')
        if username not in i2c_group.gr_mem:
            print(f"\n⚠ User '{username}' not in 'i2c' group (needed for I2C sensors)")
            add_group = input("Add user to i2c group? (y/n) [y]: ").strip().lower()
            if add_group in ['', 'y', 'yes']:
                try:
                    subprocess.run(['sudo', 'usermod', '-aG', 'i2c', username], check=True)
                    print(f"✓ User '{username}' added to i2c group")
                    print("⚠ Note: Log out and log back in for group changes to take effect")
                except Exception as e:
                    print(f"⚠ Failed to add user to i2c group: {e}")
                    print(f"  Add manually with: sudo usermod -aG i2c {username}")
    except KeyError:
        # i2c group doesn't exist, skip
        pass
    except Exception as e:
        print(f"⚠ Could not check i2c group: {e}")
    
    # Copy example config files if they don't exist
    config_file = base_path / 'config.conf'
    example_config = base_path / 'example_config.conf'
    drivers_config_file = base_path / 'drivers_config.yaml'
    example_drivers_config = base_path / 'example_drivers_config.yaml'
    
    if not config_file.exists() and example_config.exists():
        print("\n📝 Creating config.conf from example...")
        try:
            import shutil
            shutil.copy(example_config, config_file)
            print("✓ config.conf created")
        except Exception as e:
            print(f"⚠ Failed to copy config.conf: {e}")
    
    if not drivers_config_file.exists() and example_drivers_config.exists():
        print("📝 Creating drivers_config.yaml from example...")
        try:
            import shutil
            shutil.copy(example_drivers_config, drivers_config_file)
            print("✓ drivers_config.yaml created")
        except Exception as e:
            print(f"⚠ Failed to copy drivers_config.yaml: {e}")
    
    # Check and setup cron job for auto-start
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        has_cron = result.returncode == 0 and ('nettemp.py' in result.stdout or 'nettemp_client' in result.stdout)
        
        if not has_cron:
            print("\n⚠ Auto-start not configured")
            setup_cron = input("Setup auto-start on boot? (y/n) [y]: ").strip().lower()
            if setup_cron in ['', 'y', 'yes']:
                venv_python = venv_path / 'bin' / 'python3'
                client_script = base_path / 'nettemp.py'
                
                if venv_python.exists() and client_script.exists():
                    cron_entry = f"@reboot /bin/sleep 30 && {venv_python} {client_script} > /dev/null 2>&1 &"
                    
                    # Get existing crontab (excluding nettemp entries)
                    existing_cron = ""
                    if result.returncode == 0 and result.stdout.strip():
                        existing_cron = '\n'.join([line for line in result.stdout.split('\n') 
                                                   if line.strip() and 'nettemp.py' not in line and 'nettemp_client' not in line])
                    
                    # Add new entry with proper newline
                    if existing_cron:
                        new_cron = existing_cron + '\n' + cron_entry + '\n'
                    else:
                        new_cron = cron_entry + '\n'
                    
                    # Install crontab
                    try:
                        proc = subprocess.run(['crontab', '-'], input=new_cron, text=True, 
                                            capture_output=True, check=True)
                        print("✓ Auto-start configured")
                        
                        # Verify it was installed
                        verify = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                        if verify.returncode == 0 and 'nettemp.py' in verify.stdout:
                            pass  # Success
                        else:
                            print("⚠ Warning: Cron entry verification failed")
                    except subprocess.CalledProcessError as e:
                        print(f"⚠ Failed to configure auto-start: {e.stderr if e.stderr else str(e)}")
                else:
                    print("⚠ Cannot setup cron: missing files")
        else:
            print("✓ Auto-start configured")
    except FileNotFoundError:
        pass  # Cron not available
    except Exception as e:
        print(f"⚠ Could not setup cron: {e}")
    
    print("\n✅ Environment ready!\n")

# Run environment check before importing other modules
check_and_setup_environment()

import yaml
import tty
import termios

# Terminal colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    LIGHT_BLUE = '\033[96m'  # Light blue (cyan)
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def print_header(text: str):
    print(f"\n{Colors.LIGHT_BLUE}{Colors.BOLD}{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}{Colors.ENDC}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def print_info(text: str):
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

def input_styled(prompt: str, default: str = "") -> str:
    if default:
        prompt_text = f"{Colors.BOLD}{prompt} [{default}]{Colors.ENDC}: "
    else:
        prompt_text = f"{Colors.BOLD}{prompt}{Colors.ENDC}: "
    
    value = input(prompt_text).strip()
    return value if value else default

def get_key():
    """Read a single keypress (including arrow keys)"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        
        # Check for escape sequences (arrow keys)
        if ch == '\x1b':
            # Arrow keys send: ESC [ A/B/C/D
            # Read next two characters to check if it's an arrow key
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return 'UP'
                elif ch3 == 'B':
                    return 'DOWN'
                elif ch3 == 'C':
                    return 'RIGHT'
                elif ch3 == 'D':
                    return 'LEFT'
            # If we get here, it was ESC key (not arrow)
            return 'ESC'
        
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def select_from_menu(options: List[str], title: str = "", selected_idx: int = 0) -> Optional[int]:
    """
    Display a menu with arrow key navigation
    Returns: selected index or None if escaped
    """
    current = selected_idx
    
    while True:
        clear_screen()
        if title:
            print_header(title)
        
        for idx, option in enumerate(options):
            if idx == current:
                print(f"{Colors.GREEN}▶ {option}{Colors.ENDC}")
            else:
                print(f"  {option}")
        
        print(f"\n{Colors.CYAN}Use ↑↓ arrows to navigate, Enter to select, Esc to cancel{Colors.ENDC}")
        
        key = get_key()
        
        if key == '':  # Ignore unknown/incomplete sequences
            continue
        elif key == 'UP':
            current = (current - 1) % len(options)
        elif key == 'DOWN':
            current = (current + 1) % len(options)
        elif key == '\r' or key == '\n':  # Enter
            return current
        elif key == 'ESC':
            return None


class I2CScanner:
    """Scan I2C bus for connected devices"""
    
    KNOWN_DEVICES = {
        0x18: "DS2482 (1-Wire bridge)",
        0x23: "BH1750 (Light sensor)",
        0x27: "HIH6130 (Humidity/Temp sensor)",
        0x29: "TSL2561/VL53L0X",
        0x39: "TSL2561 (Light sensor)",
        0x40: "HTU21D (Humidity sensor)",
        0x48: "TMP102/ADS1115 (Temp/ADC)",
        0x49: "TMP102/ADS1115 (Temp/ADC, alt)",
        0x4a: "ADS1115 (ADC)",
        0x4b: "ADS1115 (ADC)",
        0x53: "ADXL345 (Accelerometer)",
        0x60: "MPL3115A2 (Pressure/Altitude)",
        0x68: "DS1307/MPU6050",
        0x76: "BMP180/BME280 (Pressure/Temp)",
        0x77: "BMP180/BME280 (Pressure/Temp, alt)",
    }
    
    @staticmethod
    def scan() -> List[Dict[str, str]]:
        """Scan I2C bus and return list of found devices"""
        devices = []
        
        try:
            import smbus2
            bus = smbus2.SMBus(1)
            
            print_info("Scanning I2C bus...")
            for addr in range(0x03, 0x78):
                try:
                    bus.read_byte(addr)
                    device_name = I2CScanner.KNOWN_DEVICES.get(addr, "Unknown device")
                    devices.append({
                        'address': f"0x{addr:02x}",
                        'name': device_name
                    })
                except Exception:
                    pass
            
            bus.close()
        except ImportError:
            print_warning("smbus2 not installed. Install with: pip install smbus2")
        except Exception as e:
            print_error(f"I2C scan failed: {e}")
        
        return devices


class OneWireScanner:
    """Scan 1-Wire bus for connected devices"""
    
    W1_PATH = Path("/sys/bus/w1/devices")
    
    @staticmethod
    def scan() -> List[Dict[str, str]]:
        """Scan 1-Wire bus and return list of found devices"""
        devices = []
        
        if not OneWireScanner.W1_PATH.exists():
            print_warning("1-Wire kernel module not loaded. Load with: sudo modprobe w1-gpio w1-therm")
            return devices
        
        print_info("Scanning 1-Wire bus...")
        for device_dir in OneWireScanner.W1_PATH.iterdir():
            if device_dir.is_dir() and device_dir.name != "w1_bus_master1":
                device_type = "Unknown"
                if device_dir.name.startswith("28-"):
                    device_type = "DS18B20 (Temperature)"
                elif device_dir.name.startswith("10-"):
                    device_type = "DS18S20 (Temperature)"
                
                devices.append({
                    'rom': device_dir.name,
                    'type': device_type
                })
        
        return devices


class USBScanner:
    """Scan USB devices"""
    
    KNOWN_DEVICES = {
        '0403:6001': 'FTDI USB-Serial (FT232)',
        '0403:6015': 'FTDI USB-Serial (FT231X)',
        '10c4:ea60': 'CP2102 USB-Serial',
        '10c4:ea70': 'CP210x USB-Serial',
        '1a86:7523': 'CH340 USB-Serial',
        '1a86:5523': 'CH341 USB-Serial',
        '067b:2303': 'Prolific PL2303 USB-Serial',
        '2341:0043': 'Arduino Uno',
        '2341:0001': 'Arduino Uno (old bootloader)',
        '1a86:55d4': 'ESP32 DevKit',
        '303a:1001': 'ESP32-S2/S3',
        '10c4:ea80': 'ESP8266 NodeMCU',
    }
    
    @staticmethod
    def scan() -> List[Dict[str, str]]:
        """Scan USB devices and return list of found devices"""
        devices = []
        
        try:
            import subprocess
            print_info("Scanning USB devices...")
            
            # Try lsusb first (Linux standard)
            try:
                result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if not line.strip():
                            continue
                        # Parse: Bus 001 Device 003: ID 0403:6001 Future Technology Devices International, Ltd FT232 Serial (UART) IC
                        if 'ID ' in line:
                            parts = line.split('ID ')
                            if len(parts) > 1:
                                vendor_product = parts[1].split()[0]  # e.g., "0403:6001"
                                description = ' '.join(parts[1].split()[1:]) if len(parts[1].split()) > 1 else 'Unknown'
                                
                                # Get known device name if available
                                device_name = USBScanner.KNOWN_DEVICES.get(vendor_product, description)
                                
                                devices.append({
                                    'id': vendor_product,
                                    'name': device_name,
                                    'description': description
                                })
            except FileNotFoundError:
                pass
            
            # Also check /dev for serial devices
            import glob
            serial_devices = []
            for pattern in ['/dev/ttyUSB*', '/dev/ttyACM*', '/dev/tty.usb*', '/dev/cu.usb*']:
                serial_devices.extend(glob.glob(pattern))
            
            if serial_devices:
                print_info(f"Found {len(serial_devices)} serial port(s)")
                for dev in serial_devices:
                    devices.append({
                        'id': 'serial',
                        'name': Path(dev).name,
                        'description': f'Serial port: {dev}'
                    })
            
        except Exception as e:
            print_error(f"USB scan failed: {e}")
        
        return devices


class BLEScanner:
    """Scan for Bluetooth Low Energy devices (LYWSD03MMC sensors)"""
    
    @staticmethod
    def scan():
        """Scan for BLE devices, specifically LYWSD03MMC sensors"""
        devices = []
        
        try:
            # Check if BLE libraries are available
            try:
                import adafruit_ble
                from adafruit_ble.advertising.standard import Advertisement
            except ImportError:
                print_warning("BLE libraries not installed. Install with:")
                print("  pip3 install adafruit-circuitpython-ble adafruit-circuitpython-ble-lywsd03mmc")
                return devices
            
            print_info("Scanning for BLE devices (10 seconds)...")
            print_warning("Note: May require sudo permissions")
            
            try:
                ble = adafruit_ble.BLERadio()
                found_devices = {}
                
                # Scan for devices
                for adv in ble.start_scan(Advertisement, timeout=10):
                    if adv.address and adv.address.string:
                        mac = adv.address.string
                        name = adv.complete_name or adv.short_name or "Unknown"
                        
                        # Track unique devices by MAC
                        if mac not in found_devices:
                            found_devices[mac] = {
                                'mac': mac,
                                'name': name,
                                'type': 'BLE Device'
                            }
                            
                            # Mark LYWSD03MMC sensors
                            if name == "LYWSD03MMC":
                                found_devices[mac]['type'] = 'Xiaomi Mi Temp/Humidity Sensor'
                                found_devices[mac]['description'] = f"LYWSD03MMC at {mac}"
                
                ble.stop_scan()
                
                # Convert to list
                devices = list(found_devices.values())
                
            except Exception as e:
                if "Permission denied" in str(e) or "not permitted" in str(e):
                    print_error("Permission denied. Try running with sudo:")
                    print("  sudo python3 nettemp_config.py")
                else:
                    print_error(f"BLE scan error: {e}")
        
        except Exception as e:
            print_error(f"BLE scan failed: {e}")
        
        return devices


class NettempConfigMenu:
    """Interactive configuration menu for Nettemp Client"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.config_file = self.base_path / "config.conf"
        self.drivers_file = self.base_path / "drivers_config.yaml"
        
        self.config = {}
        self.drivers_config = {}
        
        self.load_configs()
    
    def load_configs(self):
        """Load existing configuration files"""
        # Load main config - now using YAML parser
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                loaded_config = yaml.safe_load(f) or {}
                # Merge loaded config into self.config
                self.config.update(loaded_config)
                
                # Ensure cloud_servers is a list
                if 'cloud_servers' in self.config and not isinstance(self.config['cloud_servers'], list):
                    # If it's a string or something else, reset it to empty list
                    self.config['cloud_servers'] = []
        
        # Load drivers config
        if self.drivers_file.exists():
            with open(self.drivers_file, 'r') as f:
                self.drivers_config = yaml.safe_load(f) or {}
        
        # Merge missing drivers from example config
        self._merge_missing_drivers()
    
    def _merge_missing_drivers(self):
        """Add missing drivers from example_drivers_config.yaml to user's config"""
        example_file = self.base_path / "example_drivers_config.yaml"
        if not example_file.exists():
            return
        
        try:
            with open(example_file, 'r') as f:
                example_config = yaml.safe_load(f) or {}
            
            # Check for new drivers in example that user doesn't have
            new_drivers_added = []
            for driver_name, driver_settings in example_config.items():
                if driver_name not in self.drivers_config:
                    # Add new driver with default settings from example
                    self.drivers_config[driver_name] = driver_settings.copy()
                    new_drivers_added.append(driver_name)
            
            # Save updated config if new drivers were added
            if new_drivers_added:
                self.save_drivers_config()
                print_info(f"Added {len(new_drivers_added)} new driver(s): {', '.join(new_drivers_added)}")
        except Exception as e:
            # Silently fail if example config can't be read
            pass
    
    def save_main_config(self):
        """Save main configuration in YAML format with cloud_servers array"""
        config_data = {
            'group': self.config.get('group', 'my-device'),
            'device_id': self.config.get('group', 'my-device')  # device_id = group
        }
        
        # Use cloud_servers list if available, otherwise migrate from old format
        cloud_servers = self.config.get('cloud_servers', [])
        
        # If no cloud_servers list, try to migrate from old format
        if not cloud_servers:
            cloud_servers = []
            
            # Add primary cloud server if configured
            cloud_server = self.config.get('cloud_server', '')
            cloud_key = self.config.get('cloud_api_key', '')
            cloud_enabled = self.config.get('cloud_enabled') == 'true'
            
            if cloud_server and cloud_key:
                cloud_servers.append({
                    'name': 'Cloud Server',
                    'url': cloud_server,
                    'api_key': cloud_key,
                    'enabled': cloud_enabled
                })
            
            # Add local/custom server if configured and different
            local_server = self.config.get('server', '')
            local_key = self.config.get('server_api_key', '')
            
            if local_server and local_key and local_server != cloud_server:
                cloud_servers.append({
                    'name': 'Local/Custom Server',
                    'url': local_server,
                    'api_key': local_key,
                    'enabled': not cloud_enabled
                })
        else:
            # Even if cloud_servers exists, check for old server/server_api_key
            # and migrate it if not already in the list
            local_server = self.config.get('server', '')
            local_key = self.config.get('server_api_key', '')
            
            if local_server and local_key:
                # Check if this server is already in cloud_servers list
                server_exists = any(
                    s.get('url', '').rstrip('/') == local_server.rstrip('/')
                    for s in cloud_servers
                )
                
                # If not found, add it as migrated server
                if not server_exists:
                    cloud_servers.append({
                        'name': 'Local/Custom Server (migrated)',
                        'url': local_server,
                        'api_key': local_key,
                        'enabled': False,  # Default to disabled for safety
                        'format': 'legacy',
                        'verify_ssl': False
                    })
        
        if cloud_servers:
            config_data['cloud_servers'] = cloud_servers
        
        # Preserve http_bridge configuration if it exists
        if 'http_bridge' in self.config:
            config_data['http_bridge'] = self.config['http_bridge']
        
        # Write as YAML
        with open(self.config_file, 'w') as f:
            f.write("# Nettemp Client Configuration\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        
        print_success(f"Configuration saved to {self.config_file}")
    
    def save_drivers_config(self):
        """Save drivers configuration to drivers_config.yaml"""
        with open(self.drivers_file, 'w') as f:
            f.write("# Nettemp Cloud - Driver Configuration\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            yaml.dump(self.drivers_config, f, default_flow_style=False, sort_keys=False)
        
        print_success(f"Drivers configuration saved to {self.drivers_file}")
    
    def main_menu(self):
        """Display main menu"""
        current_option = 0
        
        while True:
            clear_screen()
            print_header("NETTEMP CLIENT - CONFIGURATION MENU")
            
            device_name = self.config.get('group', '')
            if not device_name or device_name == 'not set':
                print(f"Current device: {Colors.YELLOW}⚠ NOT SET - Please configure!{Colors.ENDC}\n")
            else:
                print(f"Current device: {Colors.BOLD}{device_name}{Colors.ENDC} (device_id: {device_name})\n")
            
            # Show all configured servers
            print(f"{Colors.BOLD}Configured Servers:{Colors.ENDC}")
            
            cloud_servers = self.config.get('cloud_servers', [])
            
            if cloud_servers:
                for server in cloud_servers:
                    key_preview = f"{server.get('api_key', '')[:8]}..." if len(server.get('api_key', '')) > 8 else server.get('api_key', '')
                    if server.get('enabled', True):
                        print(f"  {Colors.GREEN}▶{Colors.ENDC} {server.get('name', 'Server')}: {Colors.GREEN}{server.get('url', '')}{Colors.ENDC} (key: {key_preview})")
                    else:
                        print(f"  {Colors.CYAN}·{Colors.ENDC} {server.get('name', 'Server')}: {Colors.CYAN}{server.get('url', '')}{Colors.ENDC} (key: {key_preview})")
            else:
                print(f"  {Colors.YELLOW}No servers configured{Colors.ENDC}")
            
            enabled_drivers = sum(1 for d in self.drivers_config.values() 
                                if isinstance(d, dict) and d.get('enabled'))
            print(f"\nEnabled drivers: {Colors.BOLD}{enabled_drivers}{Colors.ENDC}")
            
            # Check cron status
            cron_enabled = self.check_cron_status()
            if cron_enabled:
                print(f"Auto-start (cron): {Colors.GREEN}✓ Configured{Colors.ENDC}")
            else:
                print(f"Auto-start (cron): {Colors.YELLOW}✗ Not configured{Colors.ENDC}")
            
            # Check background process
            bg_pid = self.check_background_process()
            if bg_pid:
                print(f"Background process: {Colors.GREEN}✓ Running (PID: {bg_pid}){Colors.ENDC}")
            else:
                print(f"Background process: {Colors.YELLOW}✗ Not running{Colors.ENDC}")
            
            # Check HTTP Bridge status
            http_bridge = self.config.get('http_bridge', {})
            if isinstance(http_bridge, dict) and http_bridge.get('enabled'):
                port = http_bridge.get('port', 8080)
                print(f"HTTP Bridge: {Colors.GREEN}✓ Enabled (port {port}){Colors.ENDC}")
            else:
                print(f"HTTP Bridge: {Colors.YELLOW}✗ Disabled{Colors.ENDC}")
            
            print("\n" + "─" * 70 + "\n")
            
            menu_options = [
                "Configure Servers",
                "Configure Device Name",
                "Configure HTTP Bridge",
                "Configure Drivers",
                "Discover Devices (I2C + 1-Wire + USB)",
                "Test & View Readings",
                "Test Connectivity & Send Data",
                "System Management (Setup/Update/Cron/Background)",
                "Exit"
            ]
            
            for idx, option in enumerate(menu_options):
                if idx == current_option:
                    print(f"{Colors.LIGHT_BLUE}▶ {option}{Colors.ENDC}")
                else:
                    print(f"  {option}")
            
            print(f"\n{Colors.LIGHT_BLUE}Use ↑↓ arrows, Enter to select, Esc to exit{Colors.ENDC}")
            
            key = get_key()
            
            if key == '':  # Ignore unknown/incomplete sequences
                continue
            elif key == 'UP':
                current_option = (current_option - 1) % len(menu_options)
            elif key == 'DOWN':
                current_option = (current_option + 1) % len(menu_options)
            elif key == '\r' or key == '\n':  # Enter
                if current_option == 0:
                    self.configure_server()
                elif current_option == 1:
                    self.configure_device_name()
                elif current_option == 2:
                    self.configure_http_bridge()
                elif current_option == 3:
                    self.configure_drivers()
                elif current_option == 4:
                    self.discover_devices()
                elif current_option == 5:
                    self.test_readings()
                elif current_option == 6:
                    self.test_connectivity()
                elif current_option == 7:
                    self.system_management()
                elif current_option == 8:
                    # Check if background process is running
                    bg_pid = self.check_background_process()
                    
                    clear_screen()
                    print_success("Configuration saved!")
                    
                    if bg_pid:
                        print(f"\n{Colors.GREEN}✓{Colors.ENDC} Background process is running (PID: {bg_pid})")
                        print("Your sensors are actively collecting data.\n")
                        try:
                            input(f"Press Enter to exit...")
                        except (KeyboardInterrupt, EOFError):
                            pass
                    else:
                        print(f"\n{Colors.YELLOW}⚠{Colors.ENDC}  No background process detected!")
                        print("To start data collection, the nettemp_client.py process needs to be running.\n")
                        
                        start_now = input_styled("Start background process now? (y/n)", "y")
                        
                        if start_now.lower() == 'y':
                            # Start the background client
                            client_script = self.base_path / 'nettemp_client.py'
                            if not client_script.exists():
                                print_error("nettemp_client.py not found!")
                            else:
                                try:
                                    # Use venv python if available
                                    venv_python = self.base_path / 'venv' / 'bin' / 'python3'
                                    python_cmd = str(venv_python) if venv_python.exists() else 'python3'
                                    
                                    # Start process in background
                                    log_file = self.base_path / 'nettemp_client.log'
                                    with open(log_file, 'a') as f:
                                        subprocess.Popen(
                                            [python_cmd, str(client_script)],
                                            cwd=str(self.base_path),
                                            stdout=f,
                                            stderr=subprocess.STDOUT,
                                            start_new_session=True
                                        )
                                    
                                    time.sleep(1)  # Wait for process to start
                                    
                                    if self.check_background_process():
                                        print_success("\n✓ Background process started successfully!")
                                        print(f"Logs: {log_file}")
                                    else:
                                        print_error("\n✗ Failed to start process (check nettemp_client.log)")
                                        
                                except Exception as e:
                                    print_error(f"\n✗ Failed to start process: {e}")
                            
                            input(f"\n{Colors.GREEN}Press Enter to exit...{Colors.ENDC}")
                    
                    break
            elif key == 'ESC':
                # Check if background process is running
                bg_pid = self.check_background_process()
                
                clear_screen()
                print_success("Configuration saved!")
                
                if bg_pid:
                    print(f"\n{Colors.GREEN}✓{Colors.ENDC} Background process is running (PID: {bg_pid})")
                    print("Your sensors are actively collecting data.\n")
                    try:
                        input(f"Press Enter to exit...")
                    except (KeyboardInterrupt, EOFError):
                        pass
                else:
                    print(f"\n{Colors.YELLOW}⚠{Colors.ENDC}  No background process detected!")
                    print("To start data collection, the nettemp_client.py process needs to be running.\n")
                    
                    start_now = input_styled("Start background process now? (y/n)", "y")
                    
                    if start_now.lower() == 'y':
                        # Start the background client
                        client_script = self.base_path / 'nettemp_client.py'
                        if not client_script.exists():
                            print_error("nettemp_client.py not found!")
                        else:
                            try:
                                # Use venv python if available
                                venv_python = self.base_path / 'venv' / 'bin' / 'python3'
                                python_cmd = str(venv_python) if venv_python.exists() else 'python3'
                                
                                # Start process in background
                                log_file = self.base_path / 'nettemp_client.log'
                                with open(log_file, 'a') as f:
                                    subprocess.Popen(
                                        [python_cmd, str(client_script)],
                                        cwd=str(self.base_path),
                                        stdout=f,
                                        stderr=subprocess.STDOUT,
                                        start_new_session=True
                                    )
                                
                                time.sleep(1)  # Wait for process to start
                                
                                if self.check_background_process():
                                    print_success("\n✓ Background process started successfully!")
                                    print(f"Logs: {log_file}")
                                else:
                                    print_error("\n✗ Failed to start process (check nettemp_client.log)")
                                    
                            except Exception as e:
                                print_error(f"\n✗ Failed to start process: {e}")
                        
                        input(f"\n{Colors.GREEN}Press Enter to exit...{Colors.ENDC}")
                
                break
    
    def configure_server(self):
        """Configure server settings - manage multiple servers"""
        while True:
            clear_screen()
            print_header("SERVER CONFIGURATION")
            
            # Get cloud_servers list
            if 'cloud_servers' not in self.config:
                self.config['cloud_servers'] = []
            
            cloud_servers = self.config['cloud_servers']
            
            # Show currently configured servers
            print(f"{Colors.BOLD}Currently Configured Servers:{Colors.ENDC}")
            
            if cloud_servers:
                for i, server in enumerate(cloud_servers, 1):
                    status = f"{Colors.GREEN}ENABLED{Colors.ENDC}" if server.get('enabled', True) else f"{Colors.CYAN}disabled{Colors.ENDC}"
                    key_preview = f"{server['api_key'][:8]}..." if len(server.get('api_key', '')) > 8 else server.get('api_key', '')
                    data_format = server.get('format', 'cloud')
                    ssl_status = 'SSL' if server.get('verify_ssl', True) else 'no-SSL'
                    print(f"  {i}. {server.get('name', 'Server')} - {server.get('url', '')} - {status}")
                    print(f"     API Key: {key_preview} | Format: {data_format} | {ssl_status}")
            else:
                print(f"  {Colors.YELLOW}No servers configured yet{Colors.ENDC}")
            
            print("\n" + "─" * 70 + "\n")
            
            # Menu options
            menu_options = [
                "Add new server",
                "Edit existing server",
                "Enable/Disable server",
                "Remove server",
                "Back to main menu"
            ]
            
            selected = select_from_menu(menu_options, "SERVER MANAGEMENT", 0)
            
            if selected is None or selected == 4:  # Escaped or Back
                return
            
            if selected == 0:
                # Add new server
                self._add_new_server()
            elif selected == 1:
                # Edit existing server
                if cloud_servers:
                    self._edit_server()
                else:
                    print_error("No servers configured to edit!")
                    input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            elif selected == 2:
                # Enable/Disable server
                if cloud_servers:
                    self._toggle_server()
                else:
                    print_error("No servers configured!")
                    input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            elif selected == 3:
                # Remove server
                if cloud_servers:
                    self._remove_server()
                else:
                    print_error("No servers configured to remove!")
                    input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def _add_new_server(self):
        """Add a new server to cloud_servers list"""
        clear_screen()
        print_header("ADD NEW SERVER")
        
        # List available server types
        server_options = [
            "Nettemp Cloud Primary (api.nettemp.pl)",
            "Cloud Server - Custom URL",
            "Docker/Local server (localhost)",
            "Custom server (enter any URL)"
        ]
        
        selected = select_from_menu(server_options, "SELECT SERVER TYPE", 0)
        
        if selected is None:  # Escaped
            return
        
        new_server = {}
        
        if selected == 0:
            # Nettemp Cloud (api.nettemp.pl)
            clear_screen()
            print_header("NETTEMP CLOUD - API.NETTEMP.PL")
            print_info("Get your API key from: https://app.nettemp.pl/settings/tokens")
            
            api_key = input_styled("Enter API key", 'ntk_')
            
            if api_key:
                new_server = {
                    'name': 'Nettemp Cloud Primary',
                    'url': 'https://api.nettemp.pl',
                    'api_key': api_key,
                    'enabled': True,
                    'verify_ssl': True,
                    'format': 'cloud'
                }
                self.config['cloud_servers'].append(new_server)
                print_success("Nettemp Cloud server added!")
                self.save_main_config()
                print()
            else:
                print_warning("API key is required")
        
        elif selected == 1:
            # Cloud server - custom URL
            clear_screen()
            print_header("CLOUD SERVER - CUSTOM URL")
            print_info("Enter your cloud server URL (e.g., https://nettemp.mydomain.pl)")
            
            server_url = input_styled("Enter cloud server URL", 'https://')
            server_url = server_url.rstrip('/')
            
            # Allow http:// for testing/local deployments
            if not server_url.startswith('http://') and not server_url.startswith('https://'):
                server_url = 'https://' + server_url
                print_info(f"Added https:// prefix: {server_url}")
            
            print_info(f"Get your API key from: {server_url}/settings/tokens")
            api_key = input_styled("Enter API key", 'ntk_')
            
            name = input_styled("Enter server name", 'Cloud Server')
            
            if api_key:
                new_server = {
                    'name': name,
                    'url': server_url,
                    'api_key': api_key,
                    'enabled': True,
                    'verify_ssl': False,
                    'format': 'legacy'
                }
                self.config['cloud_servers'].append(new_server)
                print_success(f"Cloud server '{name}' added!")
                print_info("Default: SSL disabled, legacy format (change in Edit Server)")
                self.save_main_config()
                print()
            else:
                print_warning("API key is required")
        
        elif selected == 2:
            # Docker/Local server
            clear_screen()
            print_header("DOCKER/LOCAL SERVER")
            print_info("Default local server URL: http://localhost:8787")
            
            server_url = input_styled("Enter local server URL", 'http://localhost:8787')
            server_url = server_url.rstrip('/')
            
            api_key = input_styled("Enter API key", 'local_key')
            name = input_styled("Enter server name", 'Docker/Local Server')
            
            new_server = {
                'name': name,
                'url': server_url,
                'api_key': api_key,
                'enabled': True,
                'verify_ssl': False,
                'format': 'legacy'
            }
            self.config['cloud_servers'].append(new_server)
            print_success(f"Local server '{name}' added!")
            print_info("Default: SSL disabled, legacy format (change in Edit Server)")
            self.save_main_config()
            print()
        
        elif selected == 3:
            # Custom server (any URL)
            clear_screen()
            print_header("CUSTOM SERVER")
            print_info("Enter any server URL (http/https)")
            
            server_url = input_styled("Enter server URL", 'http://192.168.1.100:8787')
            server_url = server_url.rstrip('/')
            
            api_key = input_styled("Enter API key", 'local_key')
            name = input_styled("Enter server name", 'Custom Server')
            
            new_server = {
                'name': name,
                'url': server_url,
                'api_key': api_key,
                'enabled': True,
                'verify_ssl': False,
                'format': 'legacy'
            }
            self.config['cloud_servers'].append(new_server)
            print_success(f"Custom server '{name}' added!")
            print_info("Default: SSL disabled, legacy format (change in Edit Server)")
            self.save_main_config()
            print()
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def _edit_server(self):
        """Edit an existing server"""
        clear_screen()
        print_header("EDIT SERVER")
        
        cloud_servers = self.config['cloud_servers']
        
        # Build menu options from server names
        server_names = [f"{i+1}. {s.get('name', 'Server')} - {s.get('url', '')}" 
                        for i, s in enumerate(cloud_servers)]
        
        selected = select_from_menu(server_names, "SELECT SERVER TO EDIT", 0)
        
        if selected is None:
            return
        
        server = cloud_servers[selected]
        
        clear_screen()
        print_header(f"EDIT: {server.get('name', 'Server')}")
        
        # Edit fields
        print_info("Press Enter to keep current value")
        
        name = input_styled("Server name", server.get('name', ''))
        if name:
            server['name'] = name
        
        url = input_styled("Server URL", server.get('url', ''))
        if url:
            url = url.rstrip('/')
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'https://' + url
            server['url'] = url
        
        api_key = input_styled("API key", server.get('api_key', ''))
        if api_key:
            server['api_key'] = api_key
        
        # Data format option (skip for api.nettemp.pl)
        if 'api.nettemp.pl' not in server.get('url', ''):
            print("\n" + "─" * 70)
            print(f"\n{Colors.BOLD}Data Format:{Colors.ENDC}")
            current_format = server.get('format', 'cloud')
            print_info(f"Current: {current_format}")
            print_info("'cloud' = {device_id, readings: [...]} (new format)")
            print_info("'legacy' = [{rom, type, value, name}] (old format)")
            format_choice = input_styled("Data format? (cloud/legacy)", current_format)
            if format_choice:
                server['format'] = 'legacy' if format_choice.lower() in ['legacy', 'old', 'l'] else 'cloud'
        
        # SSL verification option (skip for api.nettemp.pl)
        if 'api.nettemp.pl' not in server.get('url', ''):
            print("\n" + "─" * 70)
            print(f"\n{Colors.BOLD}SSL Certificate Verification:{Colors.ENDC}")
            current_verify = server.get('verify_ssl', True)
            current_status = 'yes' if current_verify else 'no'
            print_info(f"Current: {current_status}")
            verify_choice = input_styled("Verify SSL certificate? (yes/no)", current_status)
            if verify_choice:
                server['verify_ssl'] = verify_choice.lower() in ['yes', 'y', 'true', '1']
        
        print_success("Server updated!")
        self.save_main_config()
        print()
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def _toggle_server(self):
        """Enable or disable a server"""
        clear_screen()
        print_header("ENABLE/DISABLE SERVER")
        
        cloud_servers = self.config['cloud_servers']
        
        # Build menu options showing current status
        server_names = []
        for i, s in enumerate(cloud_servers):
            status = "ENABLED" if s.get('enabled', True) else "disabled"
            server_names.append(f"{i+1}. {s.get('name', 'Server')} - {status}")
        
        selected = select_from_menu(server_names, "SELECT SERVER TO TOGGLE", 0)
        
        if selected is None:
            return
        
        server = cloud_servers[selected]
        server['enabled'] = not server.get('enabled', True)
        
        status = "enabled" if server['enabled'] else "disabled"
        print_success(f"Server '{server.get('name', 'Server')}' is now {status}!")
        self.save_main_config()
        print()
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def _remove_server(self):
        """Remove a server from the list"""
        clear_screen()
        print_header("REMOVE SERVER")
        
        cloud_servers = self.config['cloud_servers']
        
        # Build menu options
        server_names = [f"{i+1}. {s.get('name', 'Server')} - {s.get('url', '')}" 
                        for i, s in enumerate(cloud_servers)]
        
        selected = select_from_menu(server_names, "SELECT SERVER TO REMOVE", 0)
        
        if selected is None:
            return
        
        server = cloud_servers[selected]
        
        print_warning(f"Remove '{server.get('name', 'Server')}'?")
        confirm = input_styled("Type 'yes' to confirm", "no")
        
        if confirm.lower() == 'yes':
            cloud_servers.pop(selected)
            print_success("Server removed!")
            self.save_main_config()
            print()
        else:
            print_info("Cancelled")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def configure_http_bridge(self):
        """Configure HTTP Bridge settings"""
        current_option = 0
        
        while True:
            clear_screen()
            print_header("HTTP BRIDGE CONFIGURATION")
            
            print("HTTP Bridge accepts HTTP requests on local network and forwards")
            print("to cloud servers over HTTPS. Useful for devices without TLS support.\n")
            
            # Get current settings
            http_bridge = self.config.get('http_bridge', {})
            if not isinstance(http_bridge, dict):
                http_bridge = {}
            
            current_enabled = http_bridge.get('enabled', False)
            current_host = http_bridge.get('host', '0.0.0.0')
            current_port = http_bridge.get('port', 8080)
            current_token = http_bridge.get('auth_token', '')
            
            # Show current status
            if current_enabled:
                print(f"Status: {Colors.GREEN}Enabled{Colors.ENDC}")
                print(f"  Host: {current_host}")
                print(f"  Port: {current_port}")
                if current_token:
                    print(f"  Auth token: {current_token[:8]}...")
                
                # Show server destinations
                servers = http_bridge.get('servers', [])
                if servers:
                    print(f"  Destinations: {Colors.CYAN}{', '.join(servers)}{Colors.ENDC}")
                else:
                    print(f"  Destinations: {Colors.CYAN}All enabled servers{Colors.ENDC}")
            else:
                print(f"Status: {Colors.YELLOW}Disabled{Colors.ENDC}")
            
            print("\n" + "─" * 70 + "\n")
            
            menu_options = [
                "e: Enable/Disable",
                "h: Configure Host",
                "p: Configure Port",
                "t: Configure Auth Token",
                "s: Select Destination Servers",
                "Back to Main Menu"
            ]
            
            for idx, option in enumerate(menu_options):
                if idx == current_option:
                    print(f"{Colors.LIGHT_BLUE}▶ {option}{Colors.ENDC}")
                else:
                    print(f"  {option}")
            
            print(f"\n{Colors.LIGHT_BLUE}Use ↑↓ arrows, Enter to select, Esc to go back{Colors.ENDC}")
            
            key = get_key()
            
            if key == '':
                continue
            elif key == 'UP':
                current_option = (current_option - 1) % len(menu_options)
            elif key == 'DOWN':
                current_option = (current_option + 1) % len(menu_options)
            elif key == '\r' or key == '\n':  # Enter
                if current_option == 0:  # Enable/Disable
                    enabled_str = input_styled("Enable HTTP Bridge? (y/n)", "y" if current_enabled else "n")
                    enabled = enabled_str.lower() in ['y', 'yes']
                    
                    if 'http_bridge' not in self.config or not isinstance(self.config['http_bridge'], dict):
                        self.config['http_bridge'] = {}
                    
                    self.config['http_bridge']['enabled'] = enabled
                    
                    if enabled:
                        # Set defaults if not present
                        if 'host' not in self.config['http_bridge']:
                            self.config['http_bridge']['host'] = '0.0.0.0'
                        if 'port' not in self.config['http_bridge']:
                            self.config['http_bridge']['port'] = 8080
                        print_success("\nHTTP Bridge enabled")
                    else:
                        print_info("\nHTTP Bridge disabled")
                    
                    self.save_main_config()
                    time.sleep(1)
                    
                elif current_option == 1:  # Configure Host
                    if 'http_bridge' not in self.config or not isinstance(self.config['http_bridge'], dict):
                        self.config['http_bridge'] = {'enabled': False, 'host': '0.0.0.0', 'port': 8080}
                    
                    host = input_styled("Listen host (0.0.0.0 = all interfaces)", str(current_host))
                    self.config['http_bridge']['host'] = host
                    print_success(f"\nHost set to: {host}")
                    self.save_main_config()
                    time.sleep(1)
                    
                elif current_option == 2:  # Configure Port
                    if 'http_bridge' not in self.config or not isinstance(self.config['http_bridge'], dict):
                        self.config['http_bridge'] = {'enabled': False, 'host': '0.0.0.0', 'port': 8080}
                    
                    port_str = input_styled("Listen port", str(current_port))
                    try:
                        port = int(port_str)
                        self.config['http_bridge']['port'] = port
                        print_success(f"\nPort set to: {port}")
                        self.save_main_config()
                    except:
                        print_error("\nInvalid port number")
                    time.sleep(1)
                    
                elif current_option == 3:  # Configure Auth Token
                    if 'http_bridge' not in self.config or not isinstance(self.config['http_bridge'], dict):
                        self.config['http_bridge'] = {'enabled': False, 'host': '0.0.0.0', 'port': 8080}
                    
                    auth_token = input_styled("Auth token (leave empty to remove)", current_token)
                    if auth_token:
                        self.config['http_bridge']['auth_token'] = auth_token
                        print_success(f"\nAuth token set")
                        print_info("Clients must include header: Authorization: Bearer <token>")
                    else:
                        self.config['http_bridge'].pop('auth_token', None)
                        print_info("\nAuth token removed")
                    self.save_main_config()
                    time.sleep(1)
                    
                elif current_option == 4:  # Select Servers
                    self._configure_http_bridge_servers()
                    
                elif current_option == 5:  # Back
                    break
                    
            elif key == 'e':
                # Quick toggle enable/disable
                if 'http_bridge' not in self.config or not isinstance(self.config['http_bridge'], dict):
                    self.config['http_bridge'] = {'enabled': True, 'host': '0.0.0.0', 'port': 8080}
                else:
                    self.config['http_bridge']['enabled'] = not self.config['http_bridge'].get('enabled', False)
                self.save_main_config()
            elif key in ['h', 'p', 't', 's']:
                # Quick access keys
                if key == 'h':
                    current_option = 1
                elif key == 'p':
                    current_option = 2
                elif key == 't':
                    current_option = 3
                elif key == 's':
                    current_option = 4
            elif key == 'ESC':
                break
    
    def _configure_http_bridge_servers(self):
        """Configure which servers receive data from HTTP bridge"""
        if 'http_bridge' not in self.config or not isinstance(self.config['http_bridge'], dict):
            self.config['http_bridge'] = {'enabled': False, 'host': '0.0.0.0', 'port': 8080}
        
        http_bridge = self.config['http_bridge']
        
        # Get list of all configured servers
        cloud_servers = self.config.get('cloud_servers', [])
        
        if not cloud_servers:
            clear_screen()
            print_header("SERVER SELECTION - HTTP BRIDGE")
            print_error("\nNo servers configured yet!")
            print_info("Please configure servers first in 'Configure Servers' menu.")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        # Get current server selection for HTTP bridge
        # If no 'servers' field exists (default = all enabled servers), populate with enabled servers
        if 'servers' not in http_bridge:
            current_servers = [s.get('name', f'Server {i+1}') for i, s in enumerate(cloud_servers) if s.get('enabled', True)]
        else:
            current_servers = http_bridge.get('servers', [])
        current_idx = 0
        
        while True:
            clear_screen()
            print_header("SERVER SELECTION - HTTP BRIDGE")
            
            print(f"\n{Colors.BOLD}Select which servers should receive data from HTTP Bridge:{Colors.ENDC}\n")
            print(f"{Colors.CYAN}Empty selection = send to all enabled servers (default){Colors.ENDC}\n")
            
            # Display all servers with checkboxes and navigation
            for idx, server in enumerate(cloud_servers):
                server_name = server.get('name', f'Server {idx+1}')
                server_url = server.get('url', '')
                is_enabled = server.get('enabled', True)
                is_selected = server_name in current_servers
                
                # Status indicators
                checkbox = "☑" if is_selected else "☐"
                
                # Show ENABLED (green) when selected, DISABLED (red) when not selected for HTTP bridge
                if is_selected:
                    enabled_text = f"{Colors.GREEN}[ENABLED]{Colors.ENDC}"
                else:
                    enabled_text = f"{Colors.RED}[DISABLED]{Colors.ENDC}"
                
                # Highlight current selection
                if idx == current_idx:
                    print(f"{Colors.LIGHT_BLUE}▶ {checkbox} {Colors.BOLD}{server_name}{Colors.ENDC} - {server_url} {enabled_text}")
                else:
                    print(f"  {checkbox} {server_name} - {server_url} {enabled_text}")
            
            print("\n" + "─" * 70 + "\n")
            print(f"{Colors.LIGHT_BLUE}↑↓: Navigate | Space: Toggle | c: Clear all | s: Save | Esc: Cancel{Colors.ENDC}")
            
            key = get_key()
            
            if key == '':
                continue
            elif key == 'UP':
                current_idx = (current_idx - 1) % len(cloud_servers)
            elif key == 'DOWN':
                current_idx = (current_idx + 1) % len(cloud_servers)
            elif key == ' ':  # Space to toggle
                server_name = cloud_servers[current_idx].get('name', f'Server {current_idx+1}')
                if server_name in current_servers:
                    current_servers.remove(server_name)
                else:
                    current_servers.append(server_name)
            elif key.lower() == 'c':
                # Clear all selections
                current_servers = []
            elif key.lower() == 's':
                # Save and exit
                # Check if selection matches "all enabled servers" (default behavior)
                all_enabled_names = [s.get('name', f'Server {i+1}') for i, s in enumerate(cloud_servers) if s.get('enabled', True)]
                
                if set(current_servers) == set(all_enabled_names):
                    # Selection is default, remove 'servers' field to use default behavior
                    http_bridge.pop('servers', None)
                    print_success("\nHTTP Bridge will send to all enabled servers (default)")
                else:
                    # Custom selection, save it
                    http_bridge['servers'] = current_servers
                    if current_servers:
                        print_success(f"\nHTTP Bridge will send to: {', '.join(current_servers)}")
                    else:
                        print_warning("\nNo servers selected - HTTP Bridge will not forward data!")
                
                self.save_main_config()
                time.sleep(2)
                break
            elif key == 'ESC':
                # Cancel without saving
                print_info("\nCancelled")
                time.sleep(1)
                break
    
    def configure_device_name(self):
        """Configure device name (sets both device_id and group)"""
        clear_screen()
        print_header("DEVICE NAME CONFIGURATION")
        
        print(f"\n{Colors.BOLD}Device Configuration:{Colors.ENDC}")
        print_info("This sets both 'device_id' and 'group' to the same value")
        print_info("Example: 'raspberry-pi', 'office-sensor', 'home-main'")
        
        current_device = self.config.get('group', '')
        if current_device and current_device != 'not set':
            print(f"\nCurrent device name: {Colors.BOLD}{current_device}{Colors.ENDC}")
        else:
            print(f"\n{Colors.YELLOW}No device name configured yet{Colors.ENDC}")
        
        print("\n" + "─" * 70 + "\n")
        
        default_device = self.config.get('group', 'raspberry-pi')
        if not default_device or default_device == 'not set':
            print_warning("Device name is required!")
            default_device = 'my-device'
        
        device_name = input_styled("Enter device name (device_id)", default_device)
        if device_name and device_name.strip():
            self.config['group'] = device_name.strip()
            print_success(f"Device configured: device_id={device_name.strip()}, group={device_name.strip()}")
        else:
            print_warning("Device name not changed")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def configure_drivers(self):
        """Configure sensor drivers with arrow key navigation"""
        # Scan for devices once at the beginning
        print_info("Scanning for devices...")
        i2c_devices = I2CScanner.scan()
        w1_devices = OneWireScanner.scan()
        
        # Build detection map and auto-configure I2C addresses
        detected_drivers = {}
        suggestions = self._suggest_drivers_from_i2c(i2c_devices)
        for driver, reason in suggestions.items():
            detected_drivers[driver] = reason
        
        if suggestions:
            print_success(f"Auto-configured I2C addresses for {len(suggestions)} driver(s)")
            time.sleep(1)
        
        # Check for 1-Wire devices
        if w1_devices:
            detected_drivers['w1_kernel'] = f"{len(w1_devices)} 1-Wire device(s) found"
            detected_drivers['w1_kernel_gpio'] = f"{len(w1_devices)} 1-Wire device(s) found"
        
        # Build flat list of all drivers
        all_drivers = []
        categories = {
            'System Monitoring': ['system', 'rpi', 'lm_sensors'],
            '1-Wire Sensors': ['w1_kernel', 'w1_kernel_gpio'],
            'I2C Temperature': ['tmp102', 'bme280', 'bmp180'],
            'I2C Humidity': ['htu21d', 'hih6130'],
            'I2C Light': ['bh1750', 'tsl2561'],
            'GPIO Sensors': ['dht11', 'dht22', 'hcsr04'],
            'BLE Sensors': ['lywsd03mmc'],
            'Other': ['ping', 'sdm120', 'vl53l0x', 'adxl345', 'mpl3115a2', 'capacitive_soil']
        }
        
        for category, drivers in categories.items():
            for driver in drivers:
                if driver in self.drivers_config:
                    all_drivers.append(driver)
        
        current_idx = 0
        
        while True:
            clear_screen()
            print_header("DRIVER CONFIGURATION")
            
            # Display current driver details
            if all_drivers:
                current_driver = all_drivers[current_idx]
                driver_config = self.drivers_config.get(current_driver, {})
                if driver_config is None:
                    driver_config = {}
                enabled = driver_config.get('enabled', False)
                interval = driver_config.get('read_in_sec', 300)
                interval_min = interval / 60
                
                print(f"\n{Colors.BOLD}Selected: {current_driver}{Colors.ENDC}")
                status_text = f"{Colors.GREEN}ENABLED{Colors.ENDC}" if enabled else f"{Colors.RED}DISABLED{Colors.ENDC}"
                print(f"Status: {status_text}")
                print(f"Interval: {interval}s ({interval_min:.1f} min)")
                
                # Show driver-specific configuration
                if 'i2c_address' in driver_config:
                    print(f"I2C Address: {driver_config['i2c_address']}")
                if 'gpio_pin' in driver_config:
                    print(f"GPIO Pin: {driver_config['gpio_pin']}")
                if 'hosts' in driver_config:
                    print(f"Hosts: {', '.join(driver_config['hosts'])}")
                if 'port' in driver_config:
                    print(f"Port: {driver_config['port']}")
                if 'unit' in driver_config:
                    print(f"Unit: {driver_config['unit']}")
                
                # Show server destinations
                driver_servers = driver_config.get('servers', [])
                if driver_servers:
                    print(f"Servers: {Colors.CYAN}{', '.join(driver_servers)}{Colors.ENDC}")
                else:
                    # Count enabled servers
                    cloud_servers = self.config.get('cloud_servers', [])
                    enabled_count = sum(1 for s in cloud_servers if s.get('enabled', True))
                    if enabled_count > 0:
                        print(f"Servers: {Colors.CYAN}All enabled ({enabled_count}){Colors.ENDC}")
                    else:
                        print(f"Servers: {Colors.YELLOW}None configured{Colors.ENDC}")
                
                # Show detection status
                if current_driver in detected_drivers:
                    print(f"Hardware: {Colors.GREEN}✓ {detected_drivers[current_driver]}{Colors.ENDC}")
                else:
                    print(f"Hardware: {Colors.YELLOW}? Not detected{Colors.ENDC}")
                print()
            
            print("─" * 70 + "\n")
            
            # Display all drivers
            for idx, driver in enumerate(all_drivers):
                driver_config = self.drivers_config.get(driver, {})
                if driver_config is None:
                    driver_config = {}
                enabled = driver_config.get('enabled', False)
                interval = driver_config.get('read_in_sec', 300)
                interval_min = interval / 60
                
                status = "✓" if enabled else "✗"
                status_color = Colors.GREEN if enabled else Colors.RED
                
                # Hardware detection indicator
                hw_indicator = ""
                if driver in detected_drivers:
                    hw_indicator = f" {Colors.GREEN}[HW]{Colors.ENDC}"
                
                if idx == current_idx:
                    print(f"{Colors.LIGHT_BLUE}▶ {status_color}{status}{Colors.ENDC} {Colors.BOLD}{driver:20}{Colors.ENDC} {interval} ({interval_min:.1f}min){hw_indicator}")
                else:
                    print(f"  {status_color}{status}{Colors.ENDC} {driver:20} {interval} ({interval_min:.1f}min){hw_indicator}")
            
            print(f"\n{Colors.LIGHT_BLUE}↑↓: Navigate | Space: Toggle | +/-: Interval | e: Edit | s: Servers | Esc: Back{Colors.ENDC}")
            print(f"{Colors.GREEN}[HW]{Colors.ENDC} = Hardware detected")
            
            key = get_key()
            
            if key == '':  # Ignore unknown/incomplete sequences
                continue
            elif key == 'UP':
                current_idx = (current_idx - 1) % len(all_drivers)
            elif key == 'DOWN':
                current_idx = (current_idx + 1) % len(all_drivers)
            elif key == ' ':  # Space to toggle
                driver = all_drivers[current_idx]
                if self.drivers_config.get(driver) is None:
                    self.drivers_config[driver] = {}
                driver_config = self.drivers_config[driver]
                current_state = driver_config.get('enabled', False)
                driver_config['enabled'] = not current_state
            elif key == 'e' or key == 'E':  # Edit driver settings
                self._edit_driver_settings(all_drivers[current_idx])
            elif key == 's' or key == 'S':  # Configure servers for this driver
                self._configure_driver_servers(all_drivers[current_idx])
            elif key == '+' or key == '=':  # Increase interval
                driver = all_drivers[current_idx]
                if self.drivers_config.get(driver) is None:
                    self.drivers_config[driver] = {}
                driver_config = self.drivers_config[driver]
                current_interval = driver_config.get('read_in_sec', 300)
                driver_config['read_in_sec'] = current_interval + 60
            elif key == '-':  # Decrease interval
                driver = all_drivers[current_idx]
                if self.drivers_config.get(driver) is None:
                    self.drivers_config[driver] = {}
                driver_config = self.drivers_config[driver]
                current_interval = driver_config.get('read_in_sec', 300)
                new_interval = current_interval - 60
                if new_interval >= 60:
                    driver_config['read_in_sec'] = new_interval
            elif key == 'ESC':
                break
        
        # Auto-save configuration on exit
        self.save_drivers_config()
    
    def _edit_driver_settings(self, driver):
        """Edit driver-specific settings like I2C address, GPIO pin, etc."""
        if self.drivers_config.get(driver) is None:
            self.drivers_config[driver] = {}
        
        driver_config = self.drivers_config[driver]
        
        clear_screen()
        print_header(f"EDIT DRIVER SETTINGS - {driver}")
        
        # Show current settings
        print(f"\n{Colors.BOLD}Current settings:{Colors.ENDC}")
        for key, value in driver_config.items():
            if key not in ['enabled', 'read_in_sec']:
                print(f"  {key}: {value}")
        
        print("\n" + "─" * 70 + "\n")
        
        # Common driver-specific properties
        if driver in ['bme280', 'tmp102', 'bh1750', 'tsl2561', 'htu21d', 'hih6130', 'vl53l0x', 'adxl345', 'adxl343', 'mpl3115a2']:
            print(f"{Colors.CYAN}I2C Address Configuration{Colors.ENDC}")
            current = driver_config.get('i2c_address', '0x76' if driver == 'bme280' else '')
            new_value = input_styled(f"I2C address (hex, e.g. 0x76)", current)
            if new_value and new_value != current:
                driver_config['i2c_address'] = new_value
        
        if driver in ['dht11', 'dht22']:
            print(f"{Colors.CYAN}GPIO Pin Configuration{Colors.ENDC}")
            current = driver_config.get('gpio_pin', 4)
            new_value = input_styled(f"GPIO pin number", str(current))
            if new_value and new_value.isdigit():
                driver_config['gpio_pin'] = int(new_value)
        
        if driver == 'hcsr04':
            print(f"{Colors.CYAN}HC-SR04 GPIO Configuration{Colors.ENDC}")
            current_trig = driver_config.get('trigger_pin', 23)
            new_trig = input_styled(f"TRIG pin number", str(current_trig))
            if new_trig and new_trig.isdigit():
                driver_config['trigger_pin'] = int(new_trig)
            
            current_echo = driver_config.get('echo_pin', 24)
            new_echo = input_styled(f"ECHO pin number", str(current_echo))
            if new_echo and new_echo.isdigit():
                driver_config['echo_pin'] = int(new_echo)
        
        if driver == 'capacitive_soil':
            print(f"{Colors.CYAN}Capacitive Soil Moisture Sensor Configuration{Colors.ENDC}")
            current_addr = driver_config.get('i2c_address', '0x48')
            new_addr = input_styled(f"ADC I2C address", str(current_addr))
            if new_addr:
                driver_config['i2c_address'] = new_addr
            
            current_ch = driver_config.get('adc_channel', 0)
            new_ch = input_styled(f"ADC channel (0-3)", str(current_ch))
            if new_ch and new_ch.isdigit():
                driver_config['adc_channel'] = int(new_ch)
            
            current_dry = driver_config.get('voltage_dry', 3.0)
            new_dry = input_styled(f"Dry voltage (V, calibration)", str(current_dry))
            if new_dry:
                try:
                    driver_config['voltage_dry'] = float(new_dry)
                except ValueError:
                    pass
            
            current_wet = driver_config.get('voltage_wet', 1.2)
            new_wet = input_styled(f"Wet voltage (V, calibration)", str(current_wet))
            if new_wet:
                try:
                    driver_config['voltage_wet'] = float(new_wet)
                except ValueError:
                    pass
        
        if driver == 'ping':
            print(f"{Colors.CYAN}Network Hosts Configuration{Colors.ENDC}")
            current_hosts = driver_config.get('hosts', ['google.com', '8.8.8.8'])
            print(f"Current hosts: {', '.join(current_hosts)}")
            new_hosts = input_styled("Hosts (comma-separated)", ', '.join(current_hosts))
            if new_hosts:
                driver_config['hosts'] = [h.strip() for h in new_hosts.split(',')]
        
        if driver == 'sdm120':
            print(f"{Colors.CYAN}Modbus Configuration{Colors.ENDC}")
            current_port = driver_config.get('port', '/dev/ttyUSB0')
            new_port = input_styled("Serial port", current_port)
            if new_port:
                driver_config['port'] = new_port
            
            current_unit = driver_config.get('unit', 1)
            new_unit = input_styled("Modbus unit ID", str(current_unit))
            if new_unit and new_unit.isdigit():
                driver_config['unit'] = int(new_unit)
            
            current_baudrate = driver_config.get('baudrate', 2400)
            new_baudrate = input_styled("Baudrate", str(current_baudrate))
            if new_baudrate and new_baudrate.isdigit():
                driver_config['baudrate'] = int(new_baudrate)
            
            current_parity = driver_config.get('parity', 'N')
            new_parity = input_styled("Parity (N/E/O)", current_parity)
            if new_parity and new_parity.upper() in ['N', 'E', 'O']:
                driver_config['parity'] = new_parity.upper()
        
        if driver == 'lywsd03mmc':
            print(f"{Colors.CYAN}BLE Sensor Configuration{Colors.ENDC}")
            print(f"{Colors.YELLOW}Xiaomi Mi Temperature Humidity Sensor 2 (LYWSD03MMC){Colors.ENDC}")
            
            current_name = driver_config.get('device_name', 'LYWSD03MMC')
            new_name = input_styled("BLE device name", current_name)
            if new_name:
                driver_config['device_name'] = new_name
            
            current_mac = driver_config.get('mac_address', None)
            mac_str = str(current_mac) if current_mac else 'none'
            new_mac = input_styled("MAC address (or 'none' for auto-discover)", mac_str)
            if new_mac:
                if new_mac.lower() in ['none', 'null', '']:
                    driver_config['mac_address'] = None
                else:
                    driver_config['mac_address'] = new_mac
            
            current_id = driver_config.get('sensor_id', 'default')
            new_id = input_styled("Sensor ID (unique name for multiple sensors)", current_id)
            if new_id:
                driver_config['sensor_id'] = new_id
            
            print(f"\n{Colors.YELLOW}Note: BLE sensors require sudo permissions{Colors.ENDC}")
            print(f"Install: pip3 install adafruit-circuitpython-ble adafruit-circuitpython-ble-lywsd03mmc")
        
        if driver == 'w1_kernel':
            print(f"{Colors.CYAN}1-Wire Configuration{Colors.ENDC}")
            current = driver_config.get('ds2482', False)
            use_ds2482 = input_styled("Use DS2482 I2C bridge? (true/false)", str(current).lower())
            if use_ds2482 in ['true', 'false']:
                driver_config['ds2482'] = (use_ds2482 == 'true')
        
        print_success("\nSettings updated!")
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def _configure_driver_servers(self, driver):
        """Configure which servers receive data from this driver"""
        if self.drivers_config.get(driver) is None:
            self.drivers_config[driver] = {}
        
        driver_config = self.drivers_config[driver]
        
        # Get list of all configured servers
        cloud_servers = self.config.get('cloud_servers', [])
        
        if not cloud_servers:
            clear_screen()
            print_header(f"SERVER SELECTION - {driver}")
            print_error("\nNo servers configured yet!")
            print_info("Please configure servers first in 'Configure server settings' menu.")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        # Get current server selection for this driver
        # If no 'servers' field exists (default = all enabled servers), populate with enabled servers
        if 'servers' not in driver_config:
            current_servers = [s.get('name', f'Server {i+1}') for i, s in enumerate(cloud_servers) if s.get('enabled', True)]
        else:
            current_servers = driver_config.get('servers', [])
        current_idx = 0
        
        while True:
            clear_screen()
            print_header(f"SERVER SELECTION - {driver}")
            
            print(f"\n{Colors.BOLD}Select which servers should receive data from this driver:{Colors.ENDC}\n")
            print(f"{Colors.CYAN}Empty selection = send to all enabled servers (default){Colors.ENDC}\n")
            
            # Display all servers with checkboxes and navigation
            for idx, server in enumerate(cloud_servers):
                server_name = server.get('name', f'Server {idx+1}')
                server_url = server.get('url', '')
                is_enabled = server.get('enabled', True)
                is_selected = server_name in current_servers
                
                # Status indicators
                checkbox = "☑" if is_selected else "☐"
                
                # Show ENABLED (green) when selected, DISABLED (red) when not selected for this driver
                if is_selected:
                    enabled_text = f"{Colors.GREEN}[ENABLED]{Colors.ENDC}"
                else:
                    enabled_text = f"{Colors.RED}[DISABLED]{Colors.ENDC}"
                
                # Highlight current selection
                if idx == current_idx:
                    print(f"{Colors.LIGHT_BLUE}▶ {checkbox} {Colors.BOLD}{server_name}{Colors.ENDC} - {server_url} {enabled_text}")
                else:
                    print(f"  {checkbox} {server_name} - {server_url} {enabled_text}")
            
            print("\n" + "─" * 70 + "\n")
            print(f"{Colors.LIGHT_BLUE}↑↓: Navigate | Space: Toggle | c: Clear all | s: Save | Esc: Cancel{Colors.ENDC}")
            
            key = get_key()
            
            if key == '':
                continue
            elif key == 'UP':
                current_idx = (current_idx - 1) % len(cloud_servers)
            elif key == 'DOWN':
                current_idx = (current_idx + 1) % len(cloud_servers)
            elif key == ' ':  # Space to toggle
                server_name = cloud_servers[current_idx].get('name', f'Server {current_idx+1}')
                if server_name in current_servers:
                    current_servers.remove(server_name)
                else:
                    current_servers.append(server_name)
            elif key.lower() == 'c':
                # Clear all selections
                current_servers = []
            elif key.lower() == 's':
                # Save and exit
                # Check if selection matches "all enabled servers" (default behavior)
                all_enabled_names = [s.get('name', f'Server {i+1}') for i, s in enumerate(cloud_servers) if s.get('enabled', True)]
                
                if set(current_servers) == set(all_enabled_names):
                    # Selection matches default = remove 'servers' field to use default behavior
                    if 'servers' in driver_config:
                        del driver_config['servers']
                    print_success(f"\nServer selection saved for {driver}!")
                    print_info("Will send to all enabled servers (default)")
                else:
                    # Explicit selection - save it
                    driver_config['servers'] = current_servers
                    print_success(f"\nServer selection saved for {driver}!")
                    if current_servers:
                        print_info(f"Will send to: {', '.join(current_servers)}")
                    else:
                        print_info("Will send to: NONE (no servers selected)")
                time.sleep(1.5)
                break
            elif key == 'ESC':
                # Cancel without saving
                break
    
    def discover_devices(self):
        """Discover I2C, 1-Wire, and USB devices"""
        clear_screen()
        print_header("DEVICE DISCOVERY")
        
        # I2C scan
        print(f"\n{Colors.BOLD}I2C Devices:{Colors.ENDC}")
        i2c_devices = I2CScanner.scan()
        
        if i2c_devices:
            for device in i2c_devices:
                print(f"  {Colors.GREEN}✓{Colors.ENDC} {device['address']} - {device['name']}")
            
            # Suggest drivers
            print(f"\n{Colors.BOLD}Suggested drivers to enable:{Colors.ENDC}")
            suggestions = self._suggest_drivers_from_i2c(i2c_devices)
            for driver, reason in suggestions.items():
                enabled = self.drivers_config.get(driver, {}).get('enabled', False)
                status = f"{Colors.GREEN}✓ ENABLED{Colors.ENDC}" if enabled else f"{Colors.RED}✗ DISABLED{Colors.ENDC}"
                print(f"  • {driver:20} {status} - {Colors.CYAN}{reason}{Colors.ENDC}")
        else:
            print_warning("  No I2C devices found")
        
        # 1-Wire scan
        print(f"\n{Colors.BOLD}1-Wire Devices:{Colors.ENDC}")
        w1_devices = OneWireScanner.scan()
        
        if w1_devices:
            for device in w1_devices:
                print(f"  {Colors.GREEN}✓{Colors.ENDC} {device['rom']} - {device['type']}")
            
            # Show 1-Wire driver status
            print(f"\n{Colors.BOLD}1-Wire drivers:{Colors.ENDC}")
            for driver in ['w1_kernel', 'w1_kernel_gpio']:
                if driver in self.drivers_config:
                    enabled = self.drivers_config[driver].get('enabled', False)
                    status = f"{Colors.GREEN}✓ ENABLED{Colors.ENDC}" if enabled else f"{Colors.RED}✗ DISABLED{Colors.ENDC}"
                    print(f"  • {driver:20} {status}")
        else:
            print_warning("  No 1-Wire devices found")
        
        # USB scan
        print(f"\n{Colors.BOLD}USB Devices:{Colors.ENDC}")
        usb_devices = USBScanner.scan()
        
        if usb_devices:
            for device in usb_devices:
                if device['id'] == 'serial':
                    print(f"  {Colors.GREEN}✓{Colors.ENDC} {device['name']} - {device['description']}")
                else:
                    print(f"  {Colors.GREEN}✓{Colors.ENDC} {device['id']} - {device['name']}")
            
            # Show USB-related driver suggestions
            serial_ports = [d for d in usb_devices if d['id'] == 'serial']
            if serial_ports:
                print(f"\n{Colors.BOLD}Suggested drivers for USB/Serial:{Colors.ENDC}")
                if 'sdm120' in self.drivers_config:
                    enabled = self.drivers_config['sdm120'].get('enabled', False)
                    status = f"{Colors.GREEN}✓ ENABLED{Colors.ENDC}" if enabled else f"{Colors.RED}✗ DISABLED{Colors.ENDC}"
                    print(f"  • sdm120              {status} - {Colors.CYAN}SDM120 energy meter (Modbus RTU){Colors.ENDC}")
        else:
            print_warning("  No USB devices found")
        
        # BLE scan
        print(f"\n{Colors.BOLD}BLE Devices:{Colors.ENDC}")
        ble_devices = BLEScanner.scan()
        
        if ble_devices:
            lywsd_count = 0
            for device in ble_devices:
                if device['name'] == 'LYWSD03MMC':
                    lywsd_count += 1
                    print(f"  {Colors.GREEN}✓{Colors.ENDC} {device['mac']} - {device['type']}")
            
            # Show BLE driver suggestions
            if lywsd_count > 0:
                print(f"\n{Colors.BOLD}Suggested drivers for BLE:{Colors.ENDC}")
                if 'lywsd03mmc' in self.drivers_config:
                    enabled = self.drivers_config['lywsd03mmc'].get('enabled', False)
                    status = f"{Colors.GREEN}✓ ENABLED{Colors.ENDC}" if enabled else f"{Colors.RED}✗ DISABLED{Colors.ENDC}"
                    print(f"  • lywsd03mmc          {status} - {Colors.CYAN}Found {lywsd_count} Xiaomi sensor(s){Colors.ENDC}")
        else:
            print_warning("  No BLE devices found (may require sudo)")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def _suggest_drivers_from_i2c(self, devices: List[Dict]) -> Dict[str, str]:
        """Suggest drivers based on detected I2C devices and auto-configure addresses"""
        suggestions = {}
        
        for device in devices:
            addr = device['address']
            
            if addr in ['0x76', '0x77'] and 'BME280' in device['name']:
                suggestions['bme280'] = f"Detected at {addr}"
                # Auto-configure I2C address
                if 'bme280' not in self.drivers_config or self.drivers_config['bme280'] is None:
                    self.drivers_config['bme280'] = {}
                self.drivers_config['bme280']['i2c_address'] = addr
            elif addr in ['0x76', '0x77'] and 'BMP180' in device['name']:
                suggestions['bmp180'] = f"Detected at {addr}"
                if 'bmp180' not in self.drivers_config or self.drivers_config['bmp180'] is None:
                    self.drivers_config['bmp180'] = {}
                self.drivers_config['bmp180']['i2c_address'] = addr
            elif addr == '0x23':
                suggestions['bh1750'] = f"Detected at {addr}"
                if 'bh1750' not in self.drivers_config or self.drivers_config['bh1750'] is None:
                    self.drivers_config['bh1750'] = {}
                self.drivers_config['bh1750']['i2c_address'] = addr
            elif addr == '0x29':
                # 0x29 can be TSL2561 or VL53L0X - suggest both
                if 'TSL2561' in device['name']:
                    suggestions['tsl2561'] = f"Detected at {addr}"
                    if 'tsl2561' not in self.drivers_config or self.drivers_config['tsl2561'] is None:
                        self.drivers_config['tsl2561'] = {}
                    self.drivers_config['tsl2561']['i2c_address'] = addr
                if 'VL53L0X' in device['name']:
                    suggestions['vl53l0x'] = f"Detected at {addr}"
                    if 'vl53l0x' not in self.drivers_config or self.drivers_config['vl53l0x'] is None:
                        self.drivers_config['vl53l0x'] = {}
                    self.drivers_config['vl53l0x']['i2c_address'] = addr
            elif addr == '0x39':
                suggestions['tsl2561'] = f"Detected at {addr}"
                if 'tsl2561' not in self.drivers_config or self.drivers_config['tsl2561'] is None:
                    self.drivers_config['tsl2561'] = {}
                self.drivers_config['tsl2561']['i2c_address'] = addr
            elif addr == '0x27':
                suggestions['hih6130'] = f"Detected at {addr}"
                if 'hih6130' not in self.drivers_config or self.drivers_config['hih6130'] is None:
                    self.drivers_config['hih6130'] = {}
                self.drivers_config['hih6130']['i2c_address'] = addr
            elif addr == '0x40':
                suggestions['htu21d'] = f"Detected at {addr}"
                if 'htu21d' not in self.drivers_config or self.drivers_config['htu21d'] is None:
                    self.drivers_config['htu21d'] = {}
                self.drivers_config['htu21d']['i2c_address'] = addr
            elif addr in ['0x48', '0x49', '0x4a', '0x4b']:
                # Could be TMP102 or ADS1115 ADC
                suggestions['tmp102'] = f"TMP102 temp sensor detected at {addr}"
                suggestions['capacitive_soil'] = f"ADS1115 ADC detected at {addr} (for analog sensors)"
                if 'tmp102' not in self.drivers_config or self.drivers_config['tmp102'] is None:
                    self.drivers_config['tmp102'] = {}
                self.drivers_config['tmp102']['i2c_address'] = addr
                # Also suggest capacitive soil sensor with ADC
                if 'capacitive_soil' not in self.drivers_config or self.drivers_config['capacitive_soil'] is None:
                    self.drivers_config['capacitive_soil'] = {}
                self.drivers_config['capacitive_soil']['i2c_address'] = addr
            elif addr == '0x53':
                suggestions['adxl345'] = f"Detected at {addr}"
                if 'adxl345' not in self.drivers_config or self.drivers_config['adxl345'] is None:
                    self.drivers_config['adxl345'] = {}
                self.drivers_config['adxl345']['i2c_address'] = addr
            elif addr == '0x60':
                suggestions['mpl3115a2'] = f"Detected at {addr}"
                if 'mpl3115a2' not in self.drivers_config or self.drivers_config['mpl3115a2'] is None:
                    self.drivers_config['mpl3115a2'] = {}
                self.drivers_config['mpl3115a2']['i2c_address'] = addr
            elif addr == '0x18':
                suggestions['w1_kernel'] = f"DS2482 1-Wire bridge detected at {addr}"
                if 'w1_kernel' not in self.drivers_config or self.drivers_config['w1_kernel'] is None:
                    self.drivers_config['w1_kernel'] = {}
                self.drivers_config['w1_kernel']['ds2482'] = True
        
        return suggestions
    
    def test_readings(self):
        """Test configuration and show live readings"""
        clear_screen()
        print_header("TEST READINGS")
        
        print_info("Testing sensor readings with current configuration...")
        
        # Check if BLE sensors are enabled and warn about sudo
        ble_enabled = any(
            driver in ['lywsd03mmc'] and 
            isinstance(self.drivers_config.get(driver), dict) and 
            self.drivers_config[driver].get('enabled')
            for driver in self.drivers_config
        )
        if ble_enabled and os.geteuid() != 0:
            print_warning("BLE sensors require sudo permissions. If readings fail, try:")
            print("  sudo python3 nettemp_config.py")
        
        print_warning("Press Ctrl+C to stop\n")
        
        # Import driver loader
        try:
            sys.path.insert(0, str(self.base_path))
            from driver_loader import DriverLoader
            
            loader = DriverLoader(config_file=str(self.drivers_file))
            
            try:
                # Track last read time for DHT and BLE sensors to avoid polling too fast
                sensor_last_read = {}
                dht_min_interval = 30  # DHT sensors need 30s minimum between reads in test mode
                ble_min_interval = 10  # BLE sensors need 10s minimum between reads in test mode
                
                while True:
                    print(f"\n{Colors.BOLD}[{time.strftime('%H:%M:%S')}]{Colors.ENDC}")
                    
                    for driver_name, driver_config in self.drivers_config.items():
                        if not isinstance(driver_config, dict):
                            continue
                        
                        if driver_config.get('enabled'):
                            # Check if this sensor needs cooldown
                            is_dht = driver_name in ['dht11', 'dht22']
                            is_ble = driver_name in ['lywsd03mmc']
                            
                            if is_dht or is_ble:
                                min_interval = dht_min_interval if is_dht else ble_min_interval
                                last_read = sensor_last_read.get(driver_name, 0)
                                time_since = time.time() - last_read
                                if time_since < min_interval:
                                    # Skip this read, show countdown
                                    wait_time = int(min_interval - time_since)
                                    print(f"  {Colors.CYAN}{driver_name}:{Colors.ENDC} {Colors.YELLOW}(waiting {wait_time}s...){Colors.ENDC}")
                                    continue
                            
                            try:
                                readings = loader.run_driver(driver_name, driver_config)
                                if is_dht or is_ble:
                                    sensor_last_read[driver_name] = time.time()
                                
                                if readings:
                                    print(f"  {Colors.CYAN}{driver_name}:{Colors.ENDC}")
                                    for reading in readings:
                                        name = reading.get('name', reading.get('rom', 'unknown'))
                                        value = reading.get('value', 'N/A')
                                        unit = reading.get('unit', '')
                                        print(f"    {name}: {Colors.GREEN}{value}{unit}{Colors.ENDC}")
                            except Exception as e:
                                print(f"  {Colors.RED}{driver_name}: Error - {e}{Colors.ENDC}")
                    
                    time.sleep(5)
            
            except KeyboardInterrupt:
                print(f"\n\n{Colors.YELLOW}Stopped{Colors.ENDC}")
        
        except ImportError as e:
            print_error(f"Failed to import driver_loader: {e}")
        except Exception as e:
            print_error(f"Test failed: {e}")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def check_cron_status(self) -> bool:
        """Check if cron job for nettemp is configured"""
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                return 'nettemp_client' in result.stdout
            return False
        except Exception as e:
            print_error(f"Failed to check cron: {e}")
            return False
    
    def check_background_process(self) -> Optional[int]:
        """Check if nettemp_client.py is running in background. Returns PID if found."""
        try:
            # Check for PID file first
            pidfile = self.base_path / '.nettemp_client.pid'
            if pidfile.exists():
                with open(pidfile, 'r') as f:
                    pid = int(f.read().strip())
                    # Verify process is actually running
                    try:
                        os.kill(pid, 0)  # Signal 0 just checks if process exists
                        return pid
                    except OSError:
                        # Process not running, remove stale pidfile
                        pidfile.unlink()
                        return None
            
            # If no pidfile, search for running python process
            result = subprocess.run(
                ['pgrep', '-f', 'nettemp_client.py'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                # Filter out this current process
                current_pid = os.getpid()
                for pid_str in pids:
                    pid = int(pid_str)
                    if pid != current_pid:
                        return pid
            return None
        except Exception as e:
            print_warning(f"Could not check background process: {e}")
            return None
    
    def run_setup_script(self):
        """Run setup.sh script"""
        setup_script = self.base_path / 'setup.sh'
        
        if not setup_script.exists():
            print_error("setup.sh not found!")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        clear_screen()
        print_header("Running Setup Script")
        print_warning("This will install system packages and configure the client.")
        print_warning("You may be prompted for sudo password.\n")
        
        confirm = input_styled("Continue? (y/n)", "n")
        if confirm.lower() != 'y':
            return
        
        try:
            subprocess.run(['bash', str(setup_script)], check=True)
            print_success("\nSetup completed successfully!")
        except subprocess.CalledProcessError as e:
            print_error(f"Setup failed with exit code {e.returncode}")
        except Exception as e:
            print_error(f"Setup error: {e}")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def run_update_script(self):
        """Update client from GitHub repository"""
        clear_screen()
        print_header("UPDATE NETTEMP CLIENT")
        
        # Check if we're in a git repository
        if not (self.base_path / '.git').exists():
            print_error("Not a git repository!")
            print_info("Clone from: https://github.com/sosprz/nettemp_client")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        # Check if background process is running
        bg_pid = self.check_background_process()
        should_restart = False
        
        if bg_pid:
            print_warning(f"Nettemp client is running in background (PID: {bg_pid})")
            print_info("The client will be stopped during update.\n")
            should_restart = True
        
        print_info("This will:")
        print("  1. Stop running client (if active)")
        print("  2. Pull latest changes from GitHub")
        print("  3. Update Python dependencies")
        print("  4. Preserve your config files")
        print()
        
        confirm = input_styled("Continue with update? (y/n)", "n")
        if confirm.lower() != 'y':
            return
        
        try:
            # Step 1: Stop running client
            if bg_pid:
                print_info("\n[1/4] Stopping running client...")
                try:
                    os.kill(bg_pid, 15)  # SIGTERM
                    time.sleep(2)
                    print_success("Client stopped")
                except Exception as e:
                    print_warning(f"Could not stop client: {e}")
            else:
                print_info("\n[1/4] No running client detected")
            
            # Step 2: Git pull
            print_info("[2/4] Pulling latest changes from GitHub...")
            result = subprocess.run(
                ['git', 'pull', 'origin', 'main'],
                cwd=str(self.base_path),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print_error("Failed to pull changes!")
                print_error(result.stderr)
                print_info("You may need to resolve conflicts manually.")
                input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
                return
            
            print_success("Updated from GitHub")
            if 'Already up to date' in result.stdout:
                print_info("Already up to date")
            
            # Step 3: Update Python dependencies
            print_info("[3/4] Updating Python dependencies...")
            venv_pip = self.base_path / 'venv' / 'bin' / 'pip3'
            requirements = self.base_path / 'requirements.txt'
            
            if venv_pip.exists() and requirements.exists():
                result = subprocess.run(
                    [str(venv_pip), 'install', '-r', str(requirements), '--upgrade'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print_success("Dependencies updated")
                else:
                    print_warning("Some dependencies may have failed to update")
            else:
                print_warning("Virtual environment not found. Run setup first.")
            
            # Step 4: Check configs
            print_info("[4/4] Checking configuration...")
            
            config_file = self.base_path / 'config.conf'
            example_config = self.base_path / 'example_config.conf'
            
            if config_file.exists() and example_config.exists():
                print_success("config.conf preserved")
                print_info("Note: Check example_config.conf for new options")
            
            drivers_file = self.base_path / 'drivers_config.yaml'
            example_drivers = self.base_path / 'example_drivers_config.yaml'
            
            if drivers_file.exists() and example_drivers.exists():
                print_success("drivers_config.yaml preserved")
                print_info("Note: Check example_drivers_config.yaml for new options")
            
            print_success("\n✅ Update completed successfully!")
            
            # Offer to restart client
            if should_restart:
                print()
                restart = input_styled("Start client in background? (y/n)", "y")
                if restart.lower() == 'y':
                    self.start_background_client()
                    return
            
        except Exception as e:
            print_error(f"Update error: {e}")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def setup_cron_job(self):
        """Setup cron job for auto-start on boot"""
        clear_screen()
        print_header("Setup Auto-Start (Cron Job)")
        
        # Check if already configured
        if self.check_cron_status():
            print_warning("Cron job already configured!")
            print_info("Current cron jobs:")
            try:
                result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'nettemp.py' in line or 'nettemp_client' in line:
                            print(f"  {line}")
            except:
                pass
            print()
            overwrite = input_styled("Replace existing cron job? (y/n)", "n")
            if overwrite.lower() != 'y':
                input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
                return
        
        # Get venv python path
        venv_python = self.base_path / 'venv' / 'bin' / 'python3'
        if not venv_python.exists():
            print_error("Virtual environment not found! Run setup first.")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        client_script = self.base_path / 'nettemp.py'
        if not client_script.exists():
            print_error("nettemp.py not found!")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        # Create cron entry
        cron_entry = f"@reboot /bin/sleep 30 && {venv_python} {client_script} > /dev/null 2>&1 &"
        
        print_info("Will add the following cron job:")
        print(f"  {cron_entry}\n")
        print_info("This will start the client 30 seconds after system boot.\n")
        
        confirm = input_styled("Add this cron job? (y/n)", "y")
        if confirm.lower() != 'y':
            return
        
        try:
            # Get existing crontab (excluding nettemp entries)
            existing_cron = ""
            try:
                result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                if result.returncode == 0:
                    existing_cron = '\n'.join([line for line in result.stdout.split('\n') 
                                              if line and 'nettemp.py' not in line and 'nettemp_client' not in line])
            except:
                pass
            
            # Write new crontab
            new_cron = existing_cron + '\n' + cron_entry if existing_cron else cron_entry
            temp_file = self.base_path / '.nettemp_crontab'
            with open(temp_file, 'w') as f:
                f.write(new_cron + '\n')
            
            subprocess.run(['crontab', str(temp_file)], check=True)
            temp_file.unlink()
            
            print_success("Cron job added successfully!")
            print_info("The client will now start automatically on system boot.")
            
        except Exception as e:
            print_error(f"Failed to setup cron job: {e}")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def remove_cron_job(self):
        """Remove nettemp cron job"""
        clear_screen()
        print_header("Remove Auto-Start (Cron Job)")
        
        if not self.check_cron_status():
            print_info("No nettemp cron job found.")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        print_info("Current nettemp cron jobs:")
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'nettemp_client' in line:
                        print(f"  {line}")
        except:
            pass
        
        print()
        confirm = input_styled("Remove nettemp cron job? (y/n)", "n")
        if confirm.lower() != 'y':
            return
        
        try:
            # Get existing crontab without nettemp entries
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                new_cron = '\n'.join([line for line in result.stdout.split('\n') 
                                     if line and 'nettemp_client' not in line])
                
                if new_cron.strip():
                    # Write back remaining cron jobs
                    temp_file = self.base_path / '.nettemp_crontab'
                    with open(temp_file, 'w') as f:
                        f.write(new_cron + '\n')
                    subprocess.run(['crontab', str(temp_file)], check=True)
                    temp_file.unlink()
                else:
                    # Remove entire crontab if no jobs left
                    subprocess.run(['crontab', '-r'], check=True)
                
                print_success("Cron job removed successfully!")
        except Exception as e:
            print_error(f"Failed to remove cron job: {e}")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def start_background_client(self):
        """Start nettemp_client.py in background"""
        # Check if drivers_config.yaml exists, if not copy from example
        drivers_config_file = self.base_path / 'drivers_config.yaml'
        example_drivers_config = self.base_path / 'example_drivers_config.yaml'
        
        if not drivers_config_file.exists() and example_drivers_config.exists():
            print_info("Creating drivers_config.yaml from example...")
            try:
                import shutil
                shutil.copy(example_drivers_config, drivers_config_file)
                print_success("drivers_config.yaml created")
            except Exception as e:
                print_error(f"Failed to copy drivers_config.yaml: {e}")
                input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
                return
        
        # Check if already running
        bg_pid = self.check_background_process()
        if bg_pid:
            print_warning(f"Client already running in background (PID: {bg_pid})")
            stop = input_styled("Stop it first? (y/n)", "n")
            if stop.lower() == 'y':
                try:
                    os.kill(bg_pid, 15)  # SIGTERM
                    time.sleep(1)
                    print_success(f"Stopped process {bg_pid}")
                except Exception as e:
                    print_error(f"Failed to stop process: {e}")
                    input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
                    return
            else:
                input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
                return
        
        # Start in background
        client_script = self.base_path / 'nettemp_client.py'
        if not client_script.exists():
            print_error("nettemp_client.py not found!")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        try:
            # Use venv python if available
            venv_python = self.base_path / 'venv' / 'bin' / 'python3'
            python_cmd = str(venv_python) if venv_python.exists() else 'python3'
            
            # Start process in background
            process = subprocess.Popen(
                [python_cmd, str(client_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if it's still running
            if process.poll() is None:
                print_success(f"Client started in background (PID: {process.pid})")
            else:
                print_error("Client failed to start. Check logs.")
        except Exception as e:
            print_error(f"Failed to start client: {e}")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def system_management(self):
        """System management menu for setup, updates, cron, and background process"""
        current_option = 0
        
        while True:
            clear_screen()
            print_header("SYSTEM MANAGEMENT")
            
            # Check status
            cron_enabled = self.check_cron_status()
            bg_pid = self.check_background_process()
            
            print(f"{Colors.BOLD}System Status:{Colors.ENDC}")
            
            if cron_enabled:
                print(f"  Cron job: {Colors.GREEN}✓ Configured{Colors.ENDC}")
            else:
                print(f"  Cron job: {Colors.YELLOW}✗ Not configured (run setup.sh){Colors.ENDC}")
            
            if bg_pid:
                print(f"  Background process: {Colors.GREEN}✓ Running (PID: {bg_pid}){Colors.ENDC}")
            else:
                print(f"  Background process: {Colors.YELLOW}✗ Not running{Colors.ENDC}")
            
            print("\n" + "─" * 70 + "\n")
            
            menu_options = [
                "Update from GitHub",
                "Setup Auto-Start (Cron Job)",
                "Remove Auto-Start (Cron Job)",
                "View Cron Status",
                "Start Client in Background",
                "Stop Background Client",
                "Back to Main Menu"
            ]
            
            for idx, option in enumerate(menu_options):
                if idx == current_option:
                    print(f"{Colors.LIGHT_BLUE}▶ {option}{Colors.ENDC}")
                else:
                    print(f"  {option}")
            
            print(f"\n{Colors.CYAN}Use ↑↓ arrows to navigate, Enter to select, Esc to go back{Colors.ENDC}")
            
            key = get_key()
            
            if key == '':  # Ignore unknown/incomplete sequences
                continue
            elif key == 'UP':
                current_option = (current_option - 1) % len(menu_options)
            elif key == 'DOWN':
                current_option = (current_option + 1) % len(menu_options)
            elif key == '\r' or key == '\n':  # Enter
                if current_option == 0:  # Run Update
                    self.run_update_script()
                elif current_option == 1:  # Setup Auto-Start
                    self.setup_cron_job()
                elif current_option == 2:  # Remove Auto-Start
                    self.remove_cron_job()
                elif current_option == 3:  # View Cron
                    clear_screen()
                    print_header("Cron Status")
                    try:
                        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                        if result.returncode == 0:
                            if result.stdout.strip():
                                print(result.stdout)
                            else:
                                print_info("No cron jobs configured")
                        else:
                            print_info("No crontab for current user")
                    except Exception as e:
                        print_error(f"Failed to read cron: {e}")
                    input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
                elif current_option == 4:  # Start Background
                    self.start_background_client()
                elif current_option == 5:  # Stop Background
                    bg_pid = self.check_background_process()
                    if bg_pid:
                        try:
                            os.kill(bg_pid, 15)  # SIGTERM
                            time.sleep(1)
                            print_success(f"Stopped process {bg_pid}")
                        except Exception as e:
                            print_error(f"Failed to stop process: {e}")
                    else:
                        print_info("No background process running")
                    input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
                elif current_option == 6:  # Back
                    break
            elif key == 'ESC':
                break
    
    def test_connectivity(self):
        """Test server connectivity and send sample data"""
        clear_screen()
        print_header("TEST CONNECTIVITY & SEND DATA")
        
        import requests
        import urllib3
        # Disable SSL warnings for local/docker servers
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Get cloud_servers list
        cloud_servers = self.config.get('cloud_servers', [])
        
        # Build list of available servers (only enabled ones)
        available_servers = []
        for server in cloud_servers:
            if server.get('enabled', True):
                available_servers.append((
                    server.get('name', 'Server'),
                    server.get('url', ''),
                    server.get('api_key', ''),
                    server.get('verify_ssl', True),
                    server.get('format', 'cloud')
                ))
        
        if not available_servers:
            print_warning("\nNo enabled servers configured. Please configure a server first.")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        # Let user choose which server to test
        server_options = [f"{name}: {url}" for name, url, _, _, _ in available_servers]
        server_options.append("Test All Servers")
        
        selected = select_from_menu(server_options, "SELECT SERVER TO TEST")
        
        if selected is None:  # Escaped
            return
        
        # Prepare test data
        test_reading = {
            "sensor_id": "test_sensor",
            "value": 22.5,
            "unit": "°C",
            "timestamp": int(time.time())
        }
        
        clear_screen()
        print_header("TEST CONNECTIVITY & SEND DATA")
        
        # Test selected server(s)
        servers_to_test = []
        if selected == len(available_servers):  # Test all
            servers_to_test = available_servers
        else:
            servers_to_test = [available_servers[selected]]
        
        for idx, server_info in enumerate(servers_to_test):
            server_name, server_url, api_key, verify_ssl, data_format = server_info
            
            if idx > 0:
                print("\n" + "─" * 70)
            
            print(f"\n{Colors.BOLD}Testing {server_name}:{Colors.ENDC} {server_url}")
            print_info(f"Format: {data_format}")
            
            # Show SSL verification status
            if not verify_ssl:
                print_info("(SSL verification disabled)")
            
            try:
                # Test data submission (skip /health check as not all servers have it)
                print_info("Sending test data...")
                device_id = self.config.get('group', 'test_device')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                
                # Use correct format based on server configuration
                if data_format == 'legacy':
                    # Legacy format: array with rom, type, value, name, group
                    data_payload = [{
                        'rom': f'{device_id}_test_sensor',
                        'type': 'temperature',
                        'value': 22.5,
                        'name': 'Test Sensor',
                        'group': device_id
                    }]
                    endpoint = server_url  # Legacy posts to root
                else:
                    # Cloud format: device_id + readings
                    data_payload = {
                        "device_id": device_id,
                        "readings": [test_reading]
                    }
                    endpoint = f"{server_url}/api/v1/data"
                
                response = requests.post(
                    endpoint,
                    json=data_payload,
                    headers=headers,
                    timeout=10,
                    verify=verify_ssl
                )
                
                if response.status_code in [200, 201]:
                    # Try to parse JSON response
                    try:
                        result = response.json()
                        print_success(f"Data sent successfully! Response: {result}")
                    except:
                        # If not JSON, just show status
                        print_success(f"Data sent successfully! Status: {response.status_code}")
                        if response.text:
                            print_info(f"Response: {response.text[:200]}")
                else:
                    print_error(f"Failed to send data: {response.status_code}")
                    if response.text:
                        print_error(f"Response: {response.text[:500]}")
            
            except requests.exceptions.Timeout:
                print_error("Connection timeout")
                continue  # Continue to next server
            except requests.exceptions.ConnectionError:
                print_error("Cannot connect to server")
                continue  # Continue to next server
            except Exception as e:
                print_error(f"Error: {e}")
                continue  # Continue to next server
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def save_all(self):
        """Save all configuration files"""
        clear_screen()
        print_header("SAVE CONFIGURATION")
        
        self.save_main_config()
        self.save_drivers_config()
        
        print(f"\n{Colors.GREEN}Configuration saved successfully!{Colors.ENDC}")
        print("\nYou can now run the Nettemp client with:")
        print(f"  {Colors.BOLD}python3 nettemp_client.py{Colors.ENDC}")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")


def main():
    """Main entry point"""
    try:
        menu = NettempConfigMenu()
        menu.main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

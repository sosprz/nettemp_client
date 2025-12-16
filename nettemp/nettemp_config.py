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
    ./nettemp_config.py
"""

import sys
import os
import time
import subprocess
import shutil
import json
import signal
import logging
import sysconfig
from pathlib import Path
from typing import Dict, List, Optional, Any

# Allow running as a script (python nettemp_config.py) by fixing package context
if __package__ in (None, ''):
    pkg_dir = Path(__file__).resolve().parent
    parent_dir = str(pkg_dir.parent)
    pkg_dir_str = str(pkg_dir)

    # Prevent sibling nettemp.py from shadowing the nettemp package
    while pkg_dir_str in sys.path:
        sys.path.remove(pkg_dir_str)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    __package__ = "nettemp"

from nettemp.config.cron import (  # noqa: E402
    build_nettemp_reboot_entry,
    get_nettemp_cron_status,
    install_or_replace_nettemp_cron,
    remove_all_nettemp_cron,
)

from nettemp.paths import (  # noqa: E402
    get_config_dir,
    get_config_file,
    get_data_dir,
    get_drivers_file,
    get_mqtt_rules_file,
    get_pidfile,
)

def check_and_setup_environment():
    """Auto-check and install dependencies if needed"""
    base_path = Path(__file__).parent
    venv_path = base_path / 'venv'
    requirements_file = base_path / 'requirements.txt'
    if not requirements_file.exists():
        data_req = Path(sysconfig.get_path("data") or "") / "nettemp" / "requirements.txt"
        if data_req.exists():
            requirements_file = data_req
    
    print("🔍 Checking environment...")
    
    # Check if Python 3 is available
    python_missing = []
    try:
        result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
        print(f"✓ Python found: {result.stdout.strip()}")
    except FileNotFoundError:
        print("✗ Python 3 not found!")
        python_missing.append('python3')
    
    # Check if pip is available
    try:
        subprocess.run(['python3', '-m', 'pip', '--version'], capture_output=True, check=True)
        print("✓ pip installed")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("⚠ pip not found")
        python_missing.append('python3-pip')
    
    # Check if venv package is installed (Debian/Ubuntu)
    try:
        result = subprocess.run(['dpkg', '-l', 'python3-venv'], capture_output=True, text=True)
        if result.returncode == 0 and 'ii' in result.stdout:
            print("✓ python3-venv package installed")
        else:
            print("⚠ python3-venv package not found")
            python_missing.append('python3-venv')
    except FileNotFoundError:
        # dpkg not available, try module check as fallback
        try:
            subprocess.run(['python3', '-m', 'venv', '--help'], capture_output=True, check=True)
            print("✓ venv module installed")
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("⚠ venv module not found")
            python_missing.append('python3-venv')
    
    # Install missing Python components
    if python_missing:
        print(f"\nInstalling missing Python components: {', '.join(python_missing)}")
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', '-y', 'install'] + python_missing, check=True)
            print("✓ Python components installed")
        except Exception as e:
            print(f"✗ Failed to install Python components: {e}")
            sys.exit(1)
    
    # Check system tools BEFORE entering venv (so 'which' works reliably)
    missing_tools = []
    
    # Check cron
    try:
        subprocess.run(['crontab', '-l'], capture_output=True, check=False)
        print("✓ Cron installed")
    except FileNotFoundError:
        print("⚠ Cron not found")
        missing_tools.append('cron')
    
    # Check I2C tools
    i2c_paths = ['/usr/sbin/i2cdetect', '/usr/bin/i2cdetect', '/sbin/i2cdetect']
    i2c_found = any(os.path.exists(path) for path in i2c_paths)
    if i2c_found:
        print("✓ I2C tools installed")
    else:
        print("⚠ I2C tools not found")
        missing_tools.append('i2c-tools')
    
    # Check Mosquitto (MQTT broker)
    mosquitto_paths = ['/usr/sbin/mosquitto', '/usr/bin/mosquitto', '/usr/local/sbin/mosquitto']
    mosquitto_found = any(os.path.exists(path) for path in mosquitto_paths)
    if mosquitto_found:
        print("✓ Mosquitto MQTT broker installed")
    else:
        print("⚠ Mosquitto not found")
        missing_tools.append('mosquitto')
        missing_tools.append('mosquitto-clients')
    
    # Check lm-sensors
    try:
        subprocess.run(['sensors', '-v'], capture_output=True, check=False)
        print("✓ lm-sensors installed")
    except FileNotFoundError:
        print("⚠ lm-sensors not found")
        missing_tools.append('lm-sensors')
    
    # Check build tools (needed for compiling Python packages like spidev)
    build_tools_found = os.path.exists('/usr/bin/gcc') or os.path.exists('/usr/bin/cc')
    if build_tools_found:
        print("✓ Build tools installed")
    else:
        print("⚠ Build tools not found")
        missing_tools.append('build-essential')
        missing_tools.append('python3-dev')
    
    # Check git (needed for git+ packages like vcgencmd)
    git_found = os.path.exists('/usr/bin/git')
    if git_found:
        print("✓ Git installed")
    else:
        print("⚠ Git not found")
        missing_tools.append('git')
    
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
        import pwd
        import grp
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
    
    in_venv = hasattr(sys, 'base_prefix') and sys.prefix != sys.base_prefix
    managed_env = os.environ.get('PIPX_HOME') or os.environ.get('PIPX_BIN_DIR')

    if not in_venv:
        # Check/create virtual environment
        if not venv_path.exists():
            print("\n📦 Creating virtual environment...")
            try:
                subprocess.run(['python3', '-m', 'venv', str(venv_path)], check=True)
                print("✓ Virtual environment created")
            except Exception as e:
                print(f"✗ Failed to create venv: {e}")
                sys.exit(1)
        else:
            print("\n✓ Virtual environment exists")
        
        # Check if we're in venv, if not restart with venv python
        if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            venv_python = venv_path / 'bin' / 'python3'
            if venv_python.exists():
                print("🔄 Activating virtual environment...")
                os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    else:
        print("\n✓ Running inside virtual environment")
    
    # Check/install requirements (even inside venv; skip only if no file)
    try:
        if requirements_file.exists():
            print("📦 Checking Python packages...")
            if in_venv or managed_env:
                pip_cmd = [sys.executable, '-m', 'pip']
            else:
                pip_cmd = [str(venv_path / 'bin' / 'pip3')]
            list_result = subprocess.run(pip_cmd + ['list', '--format=freeze'], capture_output=True, text=True, check=True)
            installed_lines = list_result.stdout.splitlines()
            installed_packages = set()
            for line in installed_lines:
                if '==' in line:
                    pkg = line.split('==')[0].lower()
                    installed_packages.add(pkg)
                    installed_packages.add(pkg.replace('-', '_'))
                    installed_packages.add(pkg.replace('_', '-'))
                elif ' @ ' in line:
                    pkg = line.split(' @ ')[0].lower()
                    installed_packages.add(pkg)
                    installed_packages.add(pkg.replace('-', '_'))
                    installed_packages.add(pkg.replace('_', '-'))
            missing = []
            with open(requirements_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith('git+'):
                        pkg = line.split('/')[-1].replace('.git', '').lower()
                    else:
                        pkg = line.split('>=')[0].split('==')[0].split('<')[0].split('[')[0].strip().lower()
                    pkg_underscore = pkg.replace('-', '_')
                    pkg_hyphen = pkg.replace('_', '-')
                    if pkg not in installed_packages and pkg_underscore not in installed_packages and pkg_hyphen not in installed_packages:
                        missing.append(line.strip())
            if missing:
                print(f"📦 Installing {len(missing)} missing package(s)...")
                install_result = subprocess.run(pip_cmd + ["install", "-r", str(requirements_file)], capture_output=True, text=True)
                if install_result.returncode == 0:
                    print("✓ All packages installed successfully")
                else:
                    print("⚠ Some packages failed to install")
                    if "gcc" in install_result.stderr or "compiler" in install_result.stderr.lower():
                        print("  Missing C compiler. Install build tools: sudo apt-get install build-essential python3-dev")
                    if "spidev" in install_result.stderr:
                        print("  spidev package needs compilation (optional, only for SPI sensors).")
                    if install_result.stderr:
                        print(install_result.stderr.strip())
            else:
                print("✓ Python packages already installed")
        else:
            print("⚠ requirements.txt not found, skipping package check")
    except Exception as e:
        print(f"⚠ Could not verify/install Python packages: {e}")
        err_text = str(e)
        if 'install_result' in locals() and hasattr(install_result, 'stderr') and isinstance(install_result.stderr, str):
            err_text = install_result.stderr
        if "vcgencmd" in err_text:
            print("vcgencmd package needs git (optional, for Raspberry Pi CPU temperature).")
            print("  sudo apt-get install git")
        error_lines = err_text.strip().splitlines()
        relevant_errors = [line for line in error_lines if 'ERROR:' in line or 'error:' in line]
        if relevant_errors:
            print("Key errors:")
            for err in relevant_errors[-5:]:
                print(f"  {err}")
    # Copy example config files if they don't exist (into config dir)
    config_dir = get_config_dir()
    data_dir = get_data_dir()

    # Optional migration to a single directory: move editable configs into data dir,
    # unless the user explicitly pinned a different config dir.
    if not os.environ.get("NETTEMP_CONFIG_DIR") and config_dir != data_dir:
        legacy_files = ["config.conf", "drivers_config.yaml", "mqtt_rules.yaml"]
        if any((config_dir / f).exists() for f in legacy_files):
            print("\n📁 Single-directory setup option")
            print(f"Current config directory: {config_dir}")
            print(f"Recommended config directory: {data_dir}")
            migrate = input("Move config files into the recommended directory? (y/n) [n]: ").strip().lower()
            if migrate in ("y", "yes"):
                data_dir.mkdir(parents=True, exist_ok=True)
                for fname in legacy_files:
                    src = config_dir / fname
                    dst = data_dir / fname
                    if not src.exists() or dst.exists():
                        continue
                    try:
                        shutil.copy(src, dst)
                        print(f"✓ Moved {fname} → {dst}")
                    except Exception as e:
                        print(f"⚠ Failed to move {fname}: {e}")
                config_dir = data_dir

    config_dir.mkdir(parents=True, exist_ok=True)

    pkg_data_dir = Path(sysconfig.get_path("data") or "")
    os.environ.setdefault("NETTEMP_CONFIG_DIR", str(config_dir))
    config_file = get_config_file()
    example_config = base_path / 'example_config.conf'
    if not example_config.exists():
        fallback = pkg_data_dir / "nettemp" / "example_config.conf"
        if fallback.exists():
            example_config = fallback

    drivers_config_file = get_drivers_file()
    example_drivers_config = base_path / 'example_drivers_config.yaml'
    if not example_drivers_config.exists():
        fallback = pkg_data_dir / "nettemp" / "example_drivers_config.yaml"
        if fallback.exists():
            example_drivers_config = fallback

    mqtt_rules_file = get_mqtt_rules_file()
    example_mqtt_rules = base_path / 'example_mqtt_rules.yaml'
    if not example_mqtt_rules.exists():
        fallback = pkg_data_dir / "nettemp" / "example_mqtt_rules.yaml"
        if fallback.exists():
            example_mqtt_rules = fallback
    
    if not config_file.exists() and example_config.exists():
        print("\n📝 Creating config.conf from example...")
        try:
            import shutil
            shutil.copy(example_config, config_file)
            print("✓ config.conf created")
        except Exception as e:
            print(f"⚠ Failed to copy config.conf: {e}")
    
    if not drivers_config_file.exists():
        if example_drivers_config.exists():
            print("📝 Creating drivers_config.yaml from example...")
            try:
                import shutil
                shutil.copy(example_drivers_config, drivers_config_file)
                print("✓ drivers_config.yaml created")
            except Exception as e:
                print(f"⚠ Failed to copy drivers_config.yaml: {e}")
        else:
            print("⚠ drivers_config.yaml missing and no example found (example_drivers_config.yaml)")

    if not mqtt_rules_file.exists():
        if example_mqtt_rules.exists():
            print("📝 Creating mqtt_rules.yaml from example...")
            try:
                import shutil
                shutil.copy(example_mqtt_rules, mqtt_rules_file)
                print("✓ mqtt_rules.yaml created")
            except Exception as e:
                print(f"⚠ Failed to copy mqtt_rules.yaml: {e}")
        else:
            print("⚠ mqtt_rules.yaml missing and no example found (example_mqtt_rules.yaml)")
        
    # Check and setup cron job for auto-start
    try:
        status = get_nettemp_cron_status()
        if not status.has_any:
            print("\n⚠ Auto-start not configured")
            setup_cron = input("Setup auto-start on boot? (y/n) [y]: ").strip().lower()
            if setup_cron in ['', 'y', 'yes']:
                python_cmd = str(sys.executable if in_venv else venv_path / 'bin' / 'python3')
                try:
                    install_or_replace_nettemp_cron(python_cmd, config_dir=str(config_dir))
                    print("✓ Auto-start configured")
                except Exception as e:
                    print(f"⚠ Failed to configure auto-start: {e}")
        else:
            # Canonical check: if legacy entries exist, automatically replace them.
            if status.legacy_lines:
                print("\n⚠ Legacy auto-start cron entry detected — updating to package-based auto-start")
                python_cmd = str(sys.executable if in_venv else venv_path / 'bin' / 'python3')
                try:
                    install_or_replace_nettemp_cron(python_cmd, config_dir=str(config_dir))
                    print("✓ Auto-start updated")
                except Exception as e:
                    print(f"⚠ Failed to update auto-start: {e}")
            else:
                print("✓ Auto-start configured")
    except Exception as e:
        print(f"⚠ Could not setup cron: {e}")
    
    print("\n✅ Environment ready!\n")
    
    # Import yaml after venv setup
    try:
        import yaml
        return yaml
    except ImportError:
        print("⚠ Warning: yaml module not available yet")
        return None

# Run environment check before importing other modules
yaml_module = check_and_setup_environment()

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
            
            print_info("Scanning for BLE devices (20 seconds)...")
            print_warning("Note: May require sudo permissions")
            
            try:
                ble = adafruit_ble.BLERadio()
                found_devices = {}
                scan_count = 0
                
                # Scan for devices
                print("Scanning", end="", flush=True)
                for adv in ble.start_scan(Advertisement, timeout=20):
                    scan_count += 1
                    if scan_count % 10 == 0:
                        print(".", end="", flush=True)
                    
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
                            
                            # Show progress for LYWSD03MMC
                            if name == "LYWSD03MMC":
                                print(f"\n  Found: {name} at {mac}", end="", flush=True)
                
                print()  # New line after scanning
                ble.stop_scan()
                
                print(f"Scan complete. Found {len(found_devices)} unique device(s)")
                
                # Reset Bluetooth to avoid connection issues
                print("Resetting Bluetooth...")
                try:
                    import subprocess
                    subprocess.run(['sudo', 'btmgmt', 'power', 'off'], capture_output=True, timeout=5)
                    time.sleep(1)
                    subprocess.run(['sudo', 'btmgmt', 'power', 'on'], capture_output=True, timeout=5)
                    time.sleep(1)
                    print("Bluetooth reset complete")
                except Exception as reset_error:
                    print(f"Warning: Could not reset Bluetooth: {reset_error}")
                
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
        self.base_path = Path(__file__).parent  # package/scripts location
        self.config_dir = get_config_dir()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = get_config_file()
        self.drivers_file = get_drivers_file()
        self.mqtt_rules_file = get_mqtt_rules_file()
        
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
        except Exception:
            return
        
        # Check for new drivers in example that user doesn't have
        new_drivers_added = []
        for driver_name, driver_settings in example_config.items():
            if driver_name not in self.drivers_config:
                # Add new driver with default settings from example/fallback
                self.drivers_config[driver_name] = driver_settings.copy()
                new_drivers_added.append(driver_name)
        
        # Save updated config if new drivers were added
        if new_drivers_added:
            self.save_drivers_config()
            print_info(f"Added {len(new_drivers_added)} new driver(s): {', '.join(new_drivers_added)}")
    
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
            cloud_enabled_raw = self.config.get('cloud_enabled', False)
            if isinstance(cloud_enabled_raw, bool):
                cloud_enabled = cloud_enabled_raw
            else:
                cloud_enabled = str(cloud_enabled_raw).strip().lower() in ('true', '1', 'yes', 'y', 'on')
            
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
                    # Enable automatically if there are no enabled servers yet.
                    any_enabled = any(s.get('enabled', True) for s in cloud_servers)
                    cloud_servers.append({
                        'name': 'Local/Custom Server (migrated)',
                        'url': local_server,
                        'api_key': local_key,
                        'enabled': not any_enabled,
                        'format': 'legacy',
                        'verify_ssl': False
                    })
        
        if cloud_servers:
            config_data['cloud_servers'] = cloud_servers
        
        # Preserve http_bridge configuration if it exists
        if 'http_bridge' in self.config:
            config_data['http_bridge'] = self.config['http_bridge']
        
        # Preserve mqtt configuration if it exists
        if 'mqtt' in self.config:
            config_data['mqtt'] = self.config['mqtt']
        
        # Preserve theengs_gateway configuration if it exists
        if 'theengs_gateway' in self.config:
            config_data['theengs_gateway'] = self.config['theengs_gateway']
        
        # Backup existing config for safety
        try:
            if os.path.exists(self.config_file):
                shutil.copyfile(self.config_file, f"{self.config_file}.bak")
        except Exception as e:
            print_warning(f"Could not create backup for {self.config_file}: {e}")
        
        # Write as YAML
        with open(self.config_file, 'w') as f:
            f.write("# Nettemp Client Configuration\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        
        print_success(f"Configuration saved to {self.config_file}")
    
    def save_drivers_config(self):
        """Save drivers configuration to drivers_config.yaml"""
        # Backup existing drivers config for safety
        try:
            if os.path.exists(self.drivers_file):
                shutil.copyfile(self.drivers_file, f"{self.drivers_file}.bak")
        except Exception as e:
            print_warning(f"Could not create backup for {self.drivers_file}: {e}")

        with open(self.drivers_file, 'w') as f:
            f.write("# Nettemp Cloud - Driver Configuration\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            yaml.dump(self.drivers_config, f, default_flow_style=False, sort_keys=False)
        
        print_success(f"Drivers configuration saved to {self.drivers_file}")
    
    def main_menu(self):
        """Display main menu"""
        current_option = 0
        cron_enabled_cached = self.check_cron_status()
        
        while True:
            clear_screen()
            print_header("NETTEMP CLIENT - CONFIGURATION MENU")
            print(f"{Colors.CYAN}This configurator edits:{Colors.ENDC}")
            print(f"  - mqtt_rules.yaml {Colors.YELLOW}MQTT incoming topic rules{Colors.ENDC}")
            print(f"  - drivers_config.yaml {Colors.YELLOW}Local driver rules{Colors.ENDC}")
            print(f"  - config.conf {Colors.YELLOW}General settings{Colors.ENDC}\n")
            
            device_name = self.config.get('group', '')
            if not device_name or device_name == 'not set':
                print(f"Current device: {Colors.YELLOW}⚠ NOT SET - Please configure!{Colors.ENDC}\n")
            else:
                print(f"Current device: {Colors.BOLD}{device_name}{Colors.ENDC} (device_id: {device_name})\n")
            
            # Show all configured servers
            print(f"{Colors.BOLD}Configured Destination Servers:{Colors.ENDC}")
            
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

            print()  # spacing before menu options

            menu_options = [
                "View Status / Health",
                "Configure Destination Servers",
                "Configure Device Name",
                "Configure HTTP Bridge",
                "Configure MQTT Bridge",
                "Configure Theengs Gateway (BLE to MQTT)",
                "Configure Local Sensors (I2C + 1-Wire + USB + BT)",
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
                    self.show_status_summary()
                elif current_option == 1:
                    self.configure_server()
                elif current_option == 2:
                    self.configure_device_name()
                elif current_option == 3:
                    self.configure_http_bridge()
                elif current_option == 4:
                    self.configure_mqtt_bridge()
                elif current_option == 5:
                    self.configure_theengs_gateway()
                elif current_option == 6:
                    self.configure_local_sensors()
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
                                        env = os.environ.copy()
                                        env["NETTEMP_CLIENT_BG"] = "1"
                                        env["NETTEMP_CONFIG_DIR"] = str(self.config_dir)
                                        subprocess.Popen(
                                            [python_cmd, str(client_script)],
                                            cwd=str(self.base_path),
                                            stdin=subprocess.DEVNULL,
                                            stdout=f,
                                            stderr=subprocess.STDOUT,
                                            start_new_session=True,
                                            env=env,
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
                                    env = os.environ.copy()
                                    env["NETTEMP_CLIENT_BG"] = "1"
                                    env["NETTEMP_CONFIG_DIR"] = str(self.config_dir)
                                    subprocess.Popen(
                                        [python_cmd, str(client_script)],
                                        cwd=str(self.base_path),
                                        stdin=subprocess.DEVNULL,
                                        stdout=f,
                                        stderr=subprocess.STDOUT,
                                        start_new_session=True,
                                        env=env,
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
    
    def show_status_summary(self):
        """Show status/health details on demand to avoid slowing main menu."""
        clear_screen()
        print_header("STATUS / HEALTH")
        
        enabled_drivers = sum(
            1 for d in self.drivers_config.values()
            if isinstance(d, dict) and d.get('enabled')
        )
        print(f"Enabled drivers: {Colors.BOLD}{enabled_drivers}{Colors.ENDC}\n")
        
        cron_enabled = self.check_cron_status()
        if cron_enabled:
            print(f"Auto-start (cron): {Colors.GREEN}✓ Configured{Colors.ENDC}")
        else:
            print(f"Auto-start (cron): {Colors.YELLOW}✗ Not configured{Colors.ENDC}")
        
        bg_pid = self.check_background_process()
        if bg_pid:
            print(f"Background process: {Colors.GREEN}✓ Running (PID: {bg_pid}){Colors.ENDC}")
        else:
            print(f"Background process: {Colors.YELLOW}✗ Not running{Colors.ENDC}")
        
        http_bridge = self.config.get('http_bridge', {})
        if isinstance(http_bridge, dict) and http_bridge.get('enabled'):
            port = http_bridge.get('port', 8080)
            print(f"HTTP Bridge: {Colors.GREEN}✓ Enabled (port {port}){Colors.ENDC}")
        else:
            print(f"HTTP Bridge: {Colors.YELLOW}✗ Disabled{Colors.ENDC}")
        
        mqtt = self.config.get('mqtt', {})
        if isinstance(mqtt, dict) and mqtt.get('enabled'):
            mode = mqtt.get('mode', 'both')
            broker = mqtt.get('broker', 'not set')
            port = mqtt.get('port', 1883)
            print(f"MQTT Bridge: {Colors.GREEN}✓ Enabled ({mode} mode, {broker}:{port}){Colors.ENDC}")
        else:
            print(f"MQTT Bridge: {Colors.YELLOW}✗ Disabled{Colors.ENDC}")
        
        theengs = self.config.get('theengs_gateway', {})
        if isinstance(theengs, dict) and theengs.get('enabled'):
            is_running = self._check_theengs_process_running()
            if is_running:
                print(f"Theengs Gateway: {Colors.GREEN}✓ Enabled & Running{Colors.ENDC}")
            else:
                print(f"Theengs Gateway: {Colors.YELLOW}✓ Enabled (not running){Colors.ENDC}")
        else:
            is_running = self._check_theengs_process_running()
            if is_running:
                print(f"Theengs Gateway: {Colors.YELLOW}✗ Disabled (process still running){Colors.ENDC}")
            else:
                print(f"Theengs Gateway: {Colors.YELLOW}✗ Disabled{Colors.ENDC}")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")

    def configure_local_sensors(self):
        """Grouped menu for local sensor setup"""
        while True:
            clear_screen()
            print_header("LOCAL SENSORS CONFIGURATION")
            print("Configure local drivers, discover devices, and preview readings.\n")
            
            menu_options = [
                "Configure Drivers",
                "Discover Devices (I2C + 1-Wire + USB + BT)",
                "Test & View Readings",
                "Back to main menu"
            ]
            
            selected = select_from_menu(menu_options, "LOCAL SENSORS", 0)
            
            if selected is None or selected == 3:
                return
            elif selected == 0:
                self.configure_drivers()
            elif selected == 1:
                self.discover_devices()
            elif selected == 2:
                self.test_readings()
    
    def configure_server(self):
        """Configure server settings - manage multiple servers"""
        while True:
            clear_screen()
            print_header("DESTINATION SERVERS")
            
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
                "Test connectivity & send sample data",
                "Back to main menu"
            ]
            
            selected = select_from_menu(menu_options, "SERVER MANAGEMENT", 0)
            
            if selected is None or selected == 5:  # Escaped or Back
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
            elif selected == 4:
                self.test_connectivity()
    
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
    
    def _configure_mqtt_servers(self):
        """Configure which servers receive data from MQTT subscriber"""
        if 'mqtt' not in self.config or not isinstance(self.config['mqtt'], dict):
            self.config['mqtt'] = {'enabled': False}
        
        mqtt = self.config['mqtt']
        
        # Get list of all configured servers
        cloud_servers = self.config.get('cloud_servers', [])
        
        if not cloud_servers:
            clear_screen()
            print_header("SERVER SELECTION - MQTT BRIDGE")
            print_error("\nNo servers configured yet!")
            print_info("Please configure servers first in 'Configure Servers' menu.")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        # Get current server selection for MQTT subscriber
        # If no 'servers' field exists (default = all enabled servers), populate with enabled servers
        if 'servers' not in mqtt:
            current_servers = [s.get('name', f'Server {i+1}') for i, s in enumerate(cloud_servers) if s.get('enabled', True)]
        else:
            current_servers = mqtt.get('servers', [])
        current_idx = 0
        
        while True:
            clear_screen()
            print_header("SERVER SELECTION - MQTT BRIDGE (SUBSCRIBER)")
            
            print(f"\n{Colors.BOLD}Select which servers should receive data from MQTT Subscriber:{Colors.ENDC}\n")
            print(f"{Colors.CYAN}Empty selection = send to all enabled servers (default){Colors.ENDC}")
            print(f"{Colors.YELLOW}Note: This only applies to Subscriber mode (MQTT → Cloud){Colors.ENDC}\n")
            
            # Display all servers with checkboxes and navigation
            for idx, server in enumerate(cloud_servers):
                server_name = server.get('name', f'Server {idx+1}')
                server_url = server.get('url', '')
                is_enabled = server.get('enabled', True)
                is_selected = server_name in current_servers
                
                # Status indicators
                checkbox = "☑" if is_selected else "☐"
                
                # Show ENABLED (green) when selected, DISABLED (red) when not selected for MQTT
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
                    mqtt.pop('servers', None)
                    print_success("\nMQTT Subscriber will forward to all enabled servers (default)")
                else:
                    # Custom selection, save it
                    mqtt['servers'] = current_servers
                    if current_servers:
                        print_success(f"\nMQTT Subscriber will forward to: {', '.join(current_servers)}")
                    else:
                        print_warning("\nNo servers selected - MQTT Subscriber will not forward data!")
                
                self.save_main_config()
                time.sleep(2)
                break
            elif key == 'ESC':
                # Cancel without saving
                print_info("\nCancelled")
                time.sleep(1)
                break
    
    def configure_mqtt_bridge(self):
        """Configure MQTT Bridge settings"""
        current_option = 0
        
        while True:
            clear_screen()
            print_header("MQTT BRIDGE CONFIGURATION")
            
            print("MQTT Bridge can:")
            print("  • Publish sensor data to remote MQTT broker (Publisher mode)")
            print("  • Receive MQTT messages and forward to cloud servers (Subscriber mode)")
            print("  • Both modes simultaneously\n")
            
            mqtt = self.config.get('mqtt', {})
            if not isinstance(mqtt, dict):
                mqtt = {}
            # Ensure sensible defaults so empty configs don't produce blanks
            if 'mode' not in mqtt:
                mqtt['mode'] = 'subscriber'
            if not mqtt.get('broker'):
                mqtt['broker'] = '127.0.0.1'
            if 'port' not in mqtt:
                mqtt['port'] = 1883
            self.config['mqtt'] = mqtt
            self.save_main_config()

            current_enabled = mqtt.get('enabled', False)
            current_mode = mqtt.get('mode', 'subscriber')
            current_broker = mqtt.get('broker', '')
            current_port = mqtt.get('port', 1883)
            current_username = mqtt.get('username', '')
            current_tls = mqtt.get('tls', False)
            current_topic_prefix = mqtt.get('topic_prefix', 'nettemp')
            current_qos = mqtt.get('qos', 0)
            current_retain = mqtt.get('retain', False)
            current_subscribe_topics = mqtt.get('subscribe_topics', [])
            if current_subscribe_topics is None:
                current_subscribe_topics = []
            if isinstance(current_subscribe_topics, str):
                current_subscribe_topics = [current_subscribe_topics]
            current_subscribe_topics_sorted = sorted(set(current_subscribe_topics))
            current_auth_token = mqtt.get('auth_token', '')
            
            if current_enabled:
                print(f"Status: {Colors.GREEN}Enabled{Colors.ENDC}")
                print(f"  Mode: {Colors.CYAN}{current_mode}{Colors.ENDC}")
                print(f"  Broker: {current_broker}:{current_port}")
                
                if current_username:
                    print(f"  Username: {current_username}")
                if current_tls:
                    print(f"  TLS/SSL: {Colors.GREEN}Enabled{Colors.ENDC}")
                
                if current_mode in ['publisher', 'both']:
                    print(f"\n  {Colors.BOLD}Publisher Settings:{Colors.ENDC}")
                    print(f"    Topic Prefix: {current_topic_prefix}")
                    print(f"    QoS: {current_qos}")
                    print(f"    Retain: {current_retain}")
                
                if current_mode in ['subscriber', 'both']:
                    print(f"\n  {Colors.BOLD}Subscriber Settings:{Colors.ENDC}")
                    if current_subscribe_topics_sorted:
                        print(f"    Topics:")
                        for t in current_subscribe_topics_sorted:
                            print(f"      - {t}")
                    else:
                        print(f"    Topics: {Colors.YELLOW}None configured{Colors.ENDC}")
                    if current_auth_token:
                        print(f"    Auth token: {current_auth_token[:8]}...")
                    
                    servers = mqtt.get('servers', [])
                    if servers:
                        print(f"    Destinations: {Colors.CYAN}{', '.join(servers)}{Colors.ENDC}")
                    else:
                        print(f"    Destinations: {Colors.CYAN}All enabled servers{Colors.ENDC}")
            else:
                print(f"Status: {Colors.YELLOW}Disabled{Colors.ENDC}")
            
            print("\n" + "─" * 70 + "\n")
            
            menu_options = [
                "Enable Broker (server) settings",
                "Autodiscover MQTT Devices",
                "Configure Topic Rules (intervals, enable/disable)",
                "Subscriber Settings (topics, auth token)",
                "Publisher Settings (topic prefix, QoS, retain)",
                "Select Destination Servers",
                "Help / Shortcuts",
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
                if current_option == 0:  # Broker submenu
                    self._mqtt_broker_menu()
                elif current_option == 1:  # Autodiscover MQTT Devices
                    self._mqtt_autodiscover_devices()

                elif current_option == 2:  # Configure Sensor Rules
                    self._configure_mqtt_sensor_rules()

                elif current_option == 3:  # Subscriber Settings
                    if 'mqtt' not in self.config or not isinstance(self.config['mqtt'], dict):
                        self.config['mqtt'] = {'enabled': False}
                    
                    print("\nSubscriber Settings")
                    print("Receive MQTT messages and forward to cloud servers (Subscriber mode)")
                    print("\nHow it works:")
                    print("  1. MQTT broker must be running (e.g., mosquitto)")
                    print("  2. Sensors send data to MQTT broker")
                    print("  3. MQTT bridge subscribes to topics and receives sensor data")
                    print("  4. Bridge forwards data to configured cloud servers")
                    print("\nEnter topics to subscribe to (supports MQTT wildcards + and #)")
                    print("  + matches single level (e.g., home/+/temperature)")
                    print("  # matches all remaining levels (e.g., sensors/# subscribes to all)")
                    print("\nExamples:")
                    print("  sensors/#              - subscribe to all sensor topics")
                    print("  home/+/temperature     - subscribe to temperature in any room")
                    print("  devices/sensor1/data   - subscribe to specific sensor")
                    print("\nCurrent topics:")
                    if current_subscribe_topics_sorted:
                        for t in current_subscribe_topics_sorted:
                            print(f"  - {t}")
                    else:
                        print("  None")
                    
                    topics_from_editor = None
                    use_editor = input_styled("Open topics in editor? (y/n)", "n")
                    if use_editor.lower() in ['y', 'yes']:
                        temp_path = None
                        try:
                            import tempfile
                            import shlex
                            
                            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.topics') as tf:
                                temp_path = tf.name
                                tf.write('\n'.join(current_subscribe_topics_sorted))
                                tf.flush()
                            
                            editor_cmd = shlex.split(os.environ.get('EDITOR', 'nano'))
                            subprocess.run(editor_cmd + [temp_path], check=False)
                            
                            with open(temp_path, 'r') as tf:
                                topics_from_editor = [line.strip() for line in tf.readlines()]
                        except Exception as e:
                            print_error(f"\nCould not open editor: {e}")
                            topics_from_editor = None
                        finally:
                            if temp_path and os.path.exists(temp_path):
                                try:
                                    os.unlink(temp_path)
                                except Exception:
                                    pass
                    
                    topics_set = set()
                    if topics_from_editor is not None:
                        topics_set = {t for t in topics_from_editor if t}
                    else:
                        topics_str = input_styled("Topics (comma-separated)", ','.join(current_subscribe_topics_sorted) if current_subscribe_topics_sorted else '')
                    
                        if topics_str:
                            topics_set = {t.strip() for t in topics_str.split(',') if t.strip()}
                    
                    def validate_topic(t: str) -> list[str]:
                        issues = []
                        if ' ' in t or '\t' in t:
                            issues.append("contains whitespace")
                        if '//' in t:
                            issues.append("contains empty path '//'")
                        if '#' in t and not t.endswith('#'):
                            issues.append("'#' wildcard must be at end")
                        if t.endswith('/') and t != '/':
                            issues.append("trailing '/'")
                        return issues
                    
                    if topics_set:
                        topics = sorted(topics_set)
                        self.config['mqtt']['subscribe_topics'] = topics
                        print_success(f"\nSubscribe topics: {', '.join(topics)}")
                        # Warn about potential mistakes but keep saving
                        for t in topics:
                            problems = validate_topic(t)
                            if problems:
                                print_warning(f"Topic '{t}' may be invalid ({'; '.join(problems)})")
                    else:
                        self.config['mqtt']['subscribe_topics'] = []
                        print_info("\nNo subscribe topics configured")
                    
                    # Auth token for validating incoming messages
                    print("\nOptional: Auth token to validate incoming MQTT messages")
                    auth_token = input_styled("Auth Token (leave empty for none)", str(current_auth_token))
                    
                    if auth_token:
                        self.config['mqtt']['auth_token'] = auth_token
                        print_info("\nIncoming messages must include this token")
                    else:
                        self.config['mqtt'].pop('auth_token', None)
                        print_info("\nNo auth token validation")
                    
                    self.save_main_config()
                    time.sleep(2)

                elif current_option == 4:  # Publisher Settings
                    if 'mqtt' not in self.config or not isinstance(self.config['mqtt'], dict):
                        self.config['mqtt'] = {'enabled': False}
                    
                    print("\nPublisher Settings")
                    print("Topics will be: {prefix}/{device_id}/{sensor_id}/{type}")
                    
                    prefix = input_styled("Topic Prefix", str(current_topic_prefix))
                    qos_str = input_styled("QoS (0=at most once, 1=at least once, 2=exactly once)", str(current_qos))
                    retain_str = input_styled("Retain messages? (y/n)", "y" if current_retain else "n")
                    
                    try:
                        qos = int(qos_str)
                        if qos not in [0, 1, 2]:
                            print_warning("QoS must be 0, 1, or 2. Using 0.")
                            qos = 0
                        
                        retain = retain_str.lower() in ['y', 'yes']
                        
                        self.config['mqtt']['topic_prefix'] = prefix
                        self.config['mqtt']['qos'] = qos
                        self.config['mqtt']['retain'] = retain
                        
                        print_success(f"\nPublisher settings saved")
                        print_info(f"  Topic prefix: {prefix}")
                        print_info(f"  QoS: {qos}")
                        print_info(f"  Retain: {retain}")
                        
                        self.save_main_config()
                    except:
                        print_error("\nInvalid QoS value")
                    time.sleep(2)

                elif current_option == 5:  # Select Servers
                    self._configure_mqtt_servers()

                elif current_option == 6:  # Help / Shortcuts
                    clear_screen()
                    print_header("NETTEMP CLIENT - HELP")
                    print(f"{Colors.CYAN}What this tool edits:{Colors.ENDC}")
                    print("  - mqtt_rules.yaml : MQTT incoming topic rules")
                    print("  - drivers_config.yaml : Local driver rules")
                    print("  - config.conf : General settings")
                    print("\nUseful files:")
                    print("  - mqtt_topics.log : collected topics from previous runs")
                    print("\nTypical flow:")
                    print("  1) Configure MQTT broker (Enable, Mode, Broker/Port, TLS/creds)")
                    print("  2) Autodiscover MQTT Devices to pull topics from live/log data")
                    print("  3) Select devices to subscribe (topics stored in config.conf)")
                    print("  4) Adjust Topic Rules (mqtt_rules.yaml) and Drivers if needed")
                    print("\nNavigation: arrows to move, Enter to select, Esc to go back in menus.")
                    input(f"\n{Colors.GREEN}Press Enter to return...{Colors.ENDC}")
                    
                elif current_option == 7:  # Back
                    break
            
            elif key == 'ESC':
                break

    def _mqtt_broker_menu(self):
        """Broker/server settings without enable/disable prompt"""
        current_option = 0
        while True:
            clear_screen()
            print_header("MQTT BROKER (SERVER) SETTINGS")
            
            mqtt = self.config.get('mqtt', {})
            if not isinstance(mqtt, dict):
                mqtt = {}
            mqtt['enabled'] = True
            self.config['mqtt'] = mqtt
            
            current_mode = mqtt.get('mode', 'subscriber')
            current_broker = mqtt.get('broker', '')
            current_port = mqtt.get('port', 1883)
            current_username = mqtt.get('username', '')
            current_password = mqtt.get('password', '')
            current_tls = mqtt.get('tls', False)
            current_prefix = mqtt.get('topic_prefix', 'nettemp')
            current_qos = mqtt.get('qos', 0)
            current_retain = mqtt.get('retain', False)
            
            print(f"Status: {Colors.GREEN}Enabled{Colors.ENDC}")
            print(f"Mode: {Colors.CYAN}{current_mode}{Colors.ENDC}")
            print(f"Broker: {current_broker}:{current_port}")
            if current_username:
                print(f"Username: {current_username}")
            if current_tls:
                print(f"TLS/SSL: {Colors.GREEN}Enabled{Colors.ENDC}")
            print("\n" + "─" * 70 + "\n")
            
            menu_options = [
                "Set Mode (publisher/subscriber/both)",
                "Configure Broker & Port",
                "Configure Username & Password",
                "Configure Topic Prefix & QoS",
                "Toggle TLS/SSL",
                "Test Connection",
                "Back"
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
            elif key == '\r' or key == '\n':
                if current_option == 0:  # Mode
                    print("\nSelect MQTT mode:")
                    print("  1: Publisher (send sensor data to MQTT)")
                    print("  2: Subscriber (receive MQTT and forward to cloud)")
                    print("  3: Both (publisher + subscriber)")
                    mode_choice = input_styled("Mode", "3")
                    if mode_choice == '1':
                        self.config['mqtt']['mode'] = 'publisher'
                        print_success("\nMode set to: Publisher")
                    elif mode_choice == '2':
                        self.config['mqtt']['mode'] = 'subscriber'
                        print_success("\nMode set to: Subscriber")
                    else:
                        self.config['mqtt']['mode'] = 'both'
                        print_success("\nMode set to: Both")
                    self.save_main_config()
                    time.sleep(1)
                
                elif current_option == 1:  # Broker/Port
                    broker = input_styled("MQTT Broker hostname/IP", str(current_broker))
                    port_str = input_styled("MQTT Port", str(current_port))
                    try:
                        port = int(port_str)
                        self.config['mqtt']['broker'] = broker
                        self.config['mqtt']['port'] = port
                        print_success(f"\nBroker set to: {broker}:{port}")
                        self.save_main_config()
                    except:
                        print_error("\nInvalid port number")
                    time.sleep(1)
                
                elif current_option == 2:  # Username/Password
                    username = input_styled("MQTT Username (leave empty for none)", str(current_username))
                    if username:
                        password = input_styled("MQTT Password", str(current_password))
                        self.config['mqtt']['username'] = username
                        self.config['mqtt']['password'] = password
                        print_success(f"\nAuthentication configured for user: {username}")
                    else:
                        self.config['mqtt'].pop('username', None)
                        self.config['mqtt'].pop('password', None)
                        print_info("\nAuthentication removed")
                    self.save_main_config()
                    time.sleep(1)
                
                elif current_option == 3:  # Topic prefix / QoS
                    prefix = input_styled("Topic Prefix", str(current_prefix))
                    qos_str = input_styled("QoS (0/1/2)", str(current_qos))
                    retain_str = input_styled("Retain messages? (y/n)", "y" if current_retain else "n")
                    try:
                        qos = int(qos_str)
                        if qos not in [0, 1, 2]:
                            print_warning("QoS must be 0, 1, or 2. Using 0.")
                            qos = 0
                        retain = retain_str.lower() in ['y', 'yes']
                        self.config['mqtt']['topic_prefix'] = prefix
                        self.config['mqtt']['qos'] = qos
                        self.config['mqtt']['retain'] = retain
                        print_success("\nPublisher settings saved")
                        self.save_main_config()
                    except:
                        print_error("\nInvalid QoS value")
                    time.sleep(1)
                
                elif current_option == 4:  # TLS
                    tls_str = input_styled("Enable TLS/SSL? (y/n)", "y" if current_tls else "n")
                    tls = tls_str.lower() in ['y', 'yes']
                    self.config['mqtt']['tls'] = tls
                    if tls and self.config['mqtt'].get('port', 1883) == 1883:
                        use_8883 = input_styled("Change port to 8883 (standard MQTT+TLS port)? (y/n)", "y")
                        if use_8883.lower() in ['y', 'yes']:
                            self.config['mqtt']['port'] = 8883
                    self.save_main_config()
                    print_success(f"\nTLS/SSL {'enabled' if tls else 'disabled'}")
                    time.sleep(1)
                
                elif current_option == 5:  # Test connection
                    self.test_mqtt_connection()
                
                elif current_option == 6:  # Back
                    break
            
            elif key == 'ESC':
                break
    def _check_theengs_process_running(self):
        """Skip heavy process scan; rely on config flag only to avoid slowing menus."""
        return False

    def test_mqtt_connection(self):
        """Wrapper to test MQTT connectivity using current settings with safe defaults."""
        mqtt_cfg = self.config.get('mqtt', {})
        if not isinstance(mqtt_cfg, dict):
            mqtt_cfg = {}

        broker = mqtt_cfg.get('broker') or '127.0.0.1'
        port = int(mqtt_cfg.get('port', 1883) or 1883)
        username = mqtt_cfg.get('username') or ''
        password = mqtt_cfg.get('password') or ''
        tls = bool(mqtt_cfg.get('tls', False))

        # Persist defaults if they were missing
        mqtt_cfg.setdefault('broker', broker)
        mqtt_cfg.setdefault('port', port)
        mqtt_cfg.setdefault('mode', 'subscriber')
        self.config['mqtt'] = mqtt_cfg
        self.save_main_config()

        print(f"\n{Colors.BOLD}Testing connection to {broker}:{port}...{Colors.ENDC}")
        print("This may take a few seconds...\n")
        success, message = self.check_mqtt_broker_connection(broker, port, username, password, tls)
        if success:
            print_success(f"✓ {message}")
        else:
            print_error(f"✗ {message}")
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def _enable_bluetooth_experimental(self):
        """Enable Bluetooth experimental mode by modifying bluetooth.service"""
        try:
            import subprocess
            
            service_file = '/lib/systemd/system/bluetooth.service'
            
            print(f"\n{Colors.BOLD}Modifying {service_file}...{Colors.ENDC}")
            
            # Use sed to add --experimental flag
            cmd = [
                'sudo', 'sed', '-i',
                's|ExecStart=/usr/libexec/bluetooth/bluetoothd$|ExecStart=/usr/libexec/bluetooth/bluetoothd --experimental|',
                service_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print_success("✓ Modified bluetooth.service")
                
                # Reload systemd
                print("\nReloading systemd daemon...")
                subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
                print_success("✓ Reloaded systemd")
                
                # Restart bluetooth
                print("\nRestarting bluetooth service...")
                subprocess.run(['sudo', 'systemctl', 'restart', 'bluetooth'], check=True)
                print_success("✓ Restarted bluetooth")
                
                print_success("\n✓ Bluetooth experimental mode enabled!")
            else:
                print_error(f"✗ Failed to modify bluetooth.service: {result.stderr}")
                print_warning("You may need to enable it manually (see instructions above)")
                input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            
        except subprocess.CalledProcessError as e:
            print_error(f"✗ Command failed: {e}")
            print_warning("You may need to enable it manually (see instructions above)")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
        except Exception as e:
            print_error(f"✗ Error: {e}")
            print_warning("You may need to enable it manually (see instructions above)")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def _check_theengs_installed(self):
        """Check if TheengsGateway is installed"""
        try:
            import subprocess
            from pathlib import Path
            
            # Check venv first
            script_dir = Path(__file__).parent.resolve()
            venv_theengs = script_dir / 'venv' / 'bin' / 'TheengsGateway'
            
            if venv_theengs.exists():
                return True
            
            # Check system
            result = subprocess.run(['which', 'TheengsGateway'], 
                                   capture_output=True, text=True, timeout=2)
            return result.returncode == 0
        except Exception:
            return False
    
    def configure_theengs_gateway(self):
        """Configure Theengs Gateway (BLE to MQTT bridge) - Menu interface"""
        while True:
            clear_screen()
            print_header("THEENGS GATEWAY CONFIGURATION")
            
            print("Theengs Gateway scans for Bluetooth Low Energy devices")
            print("and forwards their data to MQTT broker.\n")
            print("Perfect for Xiaomi, Govee, and other BLE temperature sensors.\n")
            
            # Get current settings
            theengs = self.config.get('theengs_gateway', {})
            if not isinstance(theengs, dict):
                theengs = {}
            
            current_enabled = theengs.get('enabled', False)
            current_mqtt_host = theengs.get('mqtt_host', '127.0.0.1')
            current_mqtt_port = theengs.get('mqtt_port', 1883)
            current_adapter = theengs.get('adapter', 'hci0')
            current_scan_time = theengs.get('ble_scan_time', 10)
            current_between_scans = theengs.get('ble_time_between_scans', 30)
            current_mode = theengs.get('scanning_mode', 'passive')
            current_publish_topic = theengs.get('publish_topic', 'home/TheengsGateway/BTtoMQTT')
            
            # Show current status (lightweight)
            print("─" * 70)
            if current_enabled:
                print(f"Status: {Colors.GREEN}● Enabled{Colors.ENDC}")
            else:
                print(f"Status: {Colors.YELLOW}○ Disabled{Colors.ENDC}")
            
            if current_enabled:
                print(f"\n{Colors.BOLD}Configuration:{Colors.ENDC}")
                print(f"  MQTT Broker: {current_mqtt_host}:{current_mqtt_port}")
                print(f"  Bluetooth Adapter: {current_adapter}")
                print(f"  Scan Time: {current_scan_time}s every {current_between_scans}s")
                print(f"  Scanning Mode: {current_mode}")
                print(f"  Publish Topic: {current_publish_topic}")
            
            print("─" * 70 + "\n")
            
            # Build menu with arrow key navigation
            menu_items = []
            if current_enabled:
                menu_items.append("Disable Theengs Gateway")
            else:
                menu_items.append("Enable Theengs Gateway")
            menu_items.append("Configure Settings")
            menu_items.append("Restart Process")
            menu_items.append("Back to Main Menu")
            
            # Display menu with arrow key navigation
            current_idx = getattr(self, '_theengs_menu_idx', 0)
            for idx, item in enumerate(menu_items):
                if idx == current_idx:
                    print(f"{Colors.LIGHT_BLUE}▶ {item}{Colors.ENDC}")
                else:
                    print(f"  {item}")
            
            print(f"\n{Colors.LIGHT_BLUE}Use ↑↓ arrows, Enter to select, Esc to go back{Colors.ENDC}")
            
            key = get_key()
            
            if key == '':
                continue
            elif key == 'UP':
                current_idx = (current_idx - 1) % len(menu_items)
                self._theengs_menu_idx = current_idx
            elif key == 'DOWN':
                current_idx = (current_idx + 1) % len(menu_items)
                self._theengs_menu_idx = current_idx
            elif key == '\r' or key == '\n':  # Enter
                if current_idx == 0:
                    # Toggle enable/disable
                    self.config['theengs_gateway']['enabled'] = not current_enabled
                    self.save_main_config()
                    if not current_enabled:
                        print_success("\n✓ Theengs Gateway enabled. Restart nettemp_client to start process.")
                    else:
                        # Stop any running processes when disabling
                        self._stop_theengs_processes()
                        print_success("\n✓ Theengs Gateway disabled. Process stopped.")
                    time.sleep(2)
                elif current_idx == 1:
                    # Configure settings
                    self._configure_theengs_settings()
                elif current_idx == 2:
                    # Restart process
                    self._restart_theengs_process()
                elif current_idx == 3:
                    break
            elif key == 'ESC':
                break
    
    def _check_bluetooth_experimental(self):
        """Check if Bluetooth experimental mode is enabled"""
        try:
            result = subprocess.run(['grep', '--', '--experimental', '/lib/systemd/system/bluetooth.service'],
                                   capture_output=True, text=True, timeout=2)
            return result.returncode == 0
        except Exception:
            return False
    
    def _configure_theengs_settings(self):
        """Configure Theengs Gateway settings"""
        clear_screen()
        print_header("CONFIGURE THEENGS GATEWAY SETTINGS")
        
        theengs = self.config.get('theengs_gateway', {})
        current_mqtt_host = theengs.get('mqtt_host', '127.0.0.1')
        current_mqtt_port = theengs.get('mqtt_port', 1883)
        current_adapter = theengs.get('adapter', 'hci0')
        current_scan_time = theengs.get('ble_scan_time', 10)
        current_between_scans = theengs.get('ble_time_between_scans', 30)
        current_mode = theengs.get('scanning_mode', 'passive')
        current_publish_topic = theengs.get('publish_topic', 'home/TheengsGateway/BTtoMQTT')
        
        if 'theengs_gateway' not in self.config:
            self.config['theengs_gateway'] = {}
        
        print("\n" + "─" * 70)
        print(f"{Colors.BOLD}MQTT Broker Settings{Colors.ENDC}")
        print("─" * 70 + "\n")
        
        mqtt_host = input_styled("MQTT Broker Host", current_mqtt_host)
        mqtt_port_str = input_styled("MQTT Broker Port", str(current_mqtt_port))
        mqtt_user = input_styled("MQTT Username (leave empty for none)", theengs.get('mqtt_user', ''))
        mqtt_pass = input_styled("MQTT Password (leave empty for none)", theengs.get('mqtt_pass', ''))
        
        print("\n" + "─" * 70)
        print(f"{Colors.BOLD}Bluetooth Settings{Colors.ENDC}")
        print("─" * 70 + "\n")
        
        adapter = input_styled("Bluetooth Adapter (hci0, hci1, etc)", current_adapter)
        scan_time_str = input_styled("Scan Duration (seconds)", str(current_scan_time))
        between_scans_str = input_styled("Wait Between Scans (seconds)", str(current_between_scans))
        
        print("\nScanning Mode:")
        print("  passive - Lower power, doesn't request data from devices")
        print("  active  - Requests data, may drain battery faster")
        mode = input_styled("Scanning Mode", current_mode)
        
        print("\n" + "─" * 70)
        print(f"{Colors.BOLD}MQTT Topics{Colors.ENDC}")
        print("─" * 70 + "\n")
        
        publish_topic = input_styled("Publish Topic", current_publish_topic)
        
        # Save all settings
        try:
            self.config['theengs_gateway'] = {
                'enabled': True,
                'mqtt_host': mqtt_host,
                'mqtt_port': int(mqtt_port_str),
                'mqtt_user': mqtt_user,
                'mqtt_pass': mqtt_pass,
                'adapter': adapter,
                'ble': 1,
                'ble_scan_time': int(scan_time_str),
                'ble_time_between_scans': int(between_scans_str),
                'scanning_mode': mode,
                'publish_topic': publish_topic,
                'publish_all': 1,
                'discovery': 0,
                'log_level': 'INFO'
            }
            # Note: subscribe_topic not needed - nettemp client subscribes to specific devices
            # Note: discovery set to 0 to disable Home Assistant autodiscovery messages
            
            self.save_main_config()
            
            print_success("\n✓ Theengs Gateway settings saved!")
            print_info(f"  Broker: {mqtt_host}:{mqtt_port_str}")
            print_info(f"  Adapter: {adapter}")
            print_info(f"  Scan: {scan_time_str}s every {between_scans_str}s")
            
            # Check if Bluetooth experimental mode is needed
            if not self._check_bluetooth_experimental():
                print(f"\n{Colors.YELLOW}⚠ Bluetooth experimental mode is not enabled{Colors.ENDC}")
                enable_experimental = input_styled("Enable Bluetooth experimental mode now? (y/n)", "y")
                if enable_experimental.lower() in ['y', 'yes']:
                    self._enable_bluetooth_experimental()
            
        except ValueError:
            print_error("\nInvalid port or timing values!")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def _restart_theengs_process(self):
        """Restart Theengs Gateway process"""
        clear_screen()
        print_header("RESTART THEENGS GATEWAY PROCESS")
        
        print("\nThis will kill any running TheengsGateway processes.")
        print("The process will restart automatically when nettemp_client runs.\n")
        
        confirm = input_styled("Kill TheengsGateway processes? (y/n)", "n")
        if confirm.lower() not in ['y', 'yes']:
            return
        
        try:
            # Kill existing processes
            result = subprocess.run(['pgrep', '-f', 'TheengsGateway'],
                                   capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                print_info(f"Found {len(pids)} TheengsGateway process(es)")
                
                for pid in pids:
                    if pid:
                        try:
                            subprocess.run(['kill', '-SIGTERM', pid], timeout=2)
                            print_success(f"✓ Killed process {pid}")
                        except Exception as e:
                            print_warning(f"Could not kill process {pid}: {e}")
                
                time.sleep(2)
                
                # Check if any survived
                result = subprocess.run(['pgrep', '-f', 'TheengsGateway'],
                                       capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    print_warning("\nSome processes still running, forcing kill...")
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            try:
                                subprocess.run(['kill', '-9', pid], timeout=2)
                                print_success(f"✓ Force killed process {pid}")
                            except Exception:
                                pass
                
                print_success("\n✓ TheengsGateway processes stopped")
                print_info("Process will restart automatically with nettemp_client")
            else:
                print_warning("\nNo TheengsGateway processes found running")
                
        except Exception as e:
            print_error(f"\nError: {e}")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")

    def _stop_theengs_processes(self):
        """Kill TheengsGateway processes without prompts (used when disabling)."""
        try:
            result = subprocess.run(['pgrep', '-f', 'TheengsGateway'],
                                   capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    try:
                        subprocess.run(['kill', '-SIGTERM', pid], timeout=2)
                    except Exception:
                        pass
            time.sleep(1)
            # Force kill survivors
            result = subprocess.run(['pgrep', '-f', 'TheengsGateway'],
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            subprocess.run(['kill', '-9', pid], timeout=2)
                        except Exception:
                            pass
        except Exception:
            pass
    
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
            
            current_mac = driver_config.get('mac_address', '')
            print(f"\nCurrent MAC addresses: {current_mac or 'none'}")
            print(f"Enter MAC addresses separated by commas")
            print(f"Example: A4:C1:38:DE:45:9E,A4:C1:38:AA:BB:CC")
            new_mac = input_styled("MAC addresses (comma-separated)", current_mac)
            if new_mac:
                driver_config['mac_address'] = new_mac
            
            print(f"\n{Colors.YELLOW}Note: BLE sensors require sudo permissions{Colors.ENDC}")
            print(f"{Colors.CYAN}Use 'Discover Devices' to auto-detect sensors{Colors.ENDC}")
        
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
        """Discover I2C, 1-Wire, USB, and BLE devices"""
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
            # Show all BLE devices found
            print(f"\n{Colors.CYAN}All BLE devices discovered:{Colors.ENDC}")
            for device in ble_devices:
                device_type = device.get('type', 'BLE Device')
                print(f"  {Colors.GREEN}✓{Colors.ENDC} {device['mac']} - {device['name']} ({device_type})")
            
            # Filter LYWSD03MMC sensors
            lywsd_sensors = [d for d in ble_devices if d['name'] == 'LYWSD03MMC']
            lywsd_count = len(lywsd_sensors)
            
            # Auto-add found sensors to config
            if lywsd_count > 0:
                print(f"\n{Colors.BOLD}Auto-configuring {lywsd_count} sensor(s):{Colors.ENDC}")
                
                # Collect all MAC addresses
                mac_addresses = [device['mac'] for device in lywsd_sensors]
                
                # Create or update single lywsd03mmc entry
                if 'lywsd03mmc' not in self.drivers_config:
                    self.drivers_config['lywsd03mmc'] = {}
                
                # Get existing MACs if any
                existing_macs = self.drivers_config['lywsd03mmc'].get('mac_address', '')
                if existing_macs and isinstance(existing_macs, str) and existing_macs.strip():
                    existing_list = [m.strip() for m in existing_macs.split(',') if m.strip()]
                else:
                    existing_list = []
                
                # Add new MACs
                added_count = 0
                for mac in mac_addresses:
                    if mac not in existing_list:
                        existing_list.append(mac)
                        added_count += 1
                        print(f"  {Colors.GREEN}+{Colors.ENDC} Added {mac}")
                    else:
                        print(f"  {Colors.YELLOW}○{Colors.ENDC} {mac} already configured")
                
                # Update config
                self.drivers_config['lywsd03mmc'] = {
                    'enabled': self.drivers_config['lywsd03mmc'].get('enabled', True),
                    'read_in_sec': self.drivers_config['lywsd03mmc'].get('read_in_sec', 300),
                    'mac_address': ','.join(existing_list)
                }
                
                if added_count > 0:
                    print(f"\n{Colors.GREEN}Added {added_count} new sensor(s) to lywsd03mmc config{Colors.ENDC}")
                    # Save config automatically
                    print("Saving configuration...")
                    self.save_drivers_config()
                    print(f"{Colors.GREEN}Configuration saved{Colors.ENDC}")
                print(f"{Colors.CYAN}Use 'Configure Drivers' menu to enable if needed{Colors.ENDC}")
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
            from .driver_loader import DriverLoader
            
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
            return get_nettemp_cron_status().has_any
        except Exception as e:
            print_error(f"Failed to check cron: {e}")
            return False
    
    def _configure_mqtt_sensor_rules(self):
        """Configure MQTT sensor parsing rules (intervals, enable/disable)"""
        import yaml
        
        rules_file = self.mqtt_rules_file
        example_candidates = [
            self.base_path / 'example_mqtt_rules.yaml',
            Path(sysconfig.get_path("data") or "") / "nettemp" / 'example_mqtt_rules.yaml',
        ]
        example_file = next((p for p in example_candidates if p.exists()), None)
        
        # Copy example if mqtt_rules.yaml doesn't exist
        if not rules_file.exists():
            if example_file and example_file.exists():
                import shutil
                rules_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(example_file, rules_file)
                print_success(f"Created {rules_file} from example")
                time.sleep(1)
            else:
                print_error(f"Neither {rules_file} nor example_mqtt_rules.yaml found (checked {example_candidates})!")
                input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
                return
        
        # Load rules
        try:
            with open(rules_file, 'r') as f:
                rules_data = yaml.safe_load(f)
        except Exception as e:
            print_error(f"Failed to load {rules_file}: {e}")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        if not rules_data or 'rules' not in rules_data:
            print_error(f"Invalid rules file format!")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        rules = rules_data['rules']
        current_idx = 0
        
        while True:
            clear_screen()
            print_header("MQTT SENSOR RULES CONFIGURATION")
            
            # Display current rule details
            if rules:
                current_rule = rules[current_idx]
                name = current_rule.get('name', f'Rule {current_idx+1}')
                enabled = current_rule.get('enabled', True)
                interval = current_rule.get('interval', 60)
                interval_min = interval / 60
                topic_pattern = current_rule.get('topic_pattern', '*')
                format_type = current_rule.get('format', 'json')
                
                print(f"\n{Colors.BOLD}Selected: {name}{Colors.ENDC}")
                status_text = f"{Colors.GREEN}ENABLED{Colors.ENDC}" if enabled else f"{Colors.RED}DISABLED{Colors.ENDC}"
                print(f"Status: {status_text}")
                print(f"Interval: {interval}s ({interval_min:.1f} min)")
                print(f"Topic Pattern: {topic_pattern}")
                print(f"Format: {format_type}")
                print()
            
            print("─" * 70 + "\n")
            
            # Display all rules
            for idx, rule in enumerate(rules):
                name = rule.get('name', f'Rule {idx+1}')
                enabled = rule.get('enabled', True)
                interval = rule.get('interval', 60)
                interval_min = interval / 60
                
                status = "✓" if enabled else "✗"
                status_color = Colors.GREEN if enabled else Colors.RED
                
                if idx == current_idx:
                    print(f"{Colors.LIGHT_BLUE}▶ {status_color}{status}{Colors.ENDC} {Colors.BOLD}{name:25}{Colors.ENDC} {interval}s ({interval_min:.1f}min)")
                else:
                    print(f"  {status_color}{status}{Colors.ENDC} {name:25} {interval}s ({interval_min:.1f}min)")
            
            print(f"\n{Colors.LIGHT_BLUE}↑↓: Navigate | Space: Toggle | +/-: Interval | i: Edit Interval | Esc: Save & Back{Colors.ENDC}")
            
            key = get_key()
            
            if key == '':  # Ignore unknown/incomplete sequences
                continue
            elif key == 'UP':
                current_idx = (current_idx - 1) % len(rules)
            elif key == 'DOWN':
                current_idx = (current_idx + 1) % len(rules)
            elif key == ' ':  # Space to toggle
                rule = rules[current_idx]
                rule['enabled'] = not rule.get('enabled', True)
            elif key == 'i' or key == 'I':  # Edit interval
                rule = rules[current_idx]
                name = rule.get('name', f'Rule {current_idx+1}')
                current_interval = rule.get('interval', 60)
                
                clear_screen()
                print_header(f"CHANGE INTERVAL: {name}")
                print(f"\nCurrent interval: {current_interval}s ({current_interval // 60} minutes)")
                print("\nCommon intervals:")
                print("  60s = 1 minute")
                print("  300s = 5 minutes")
                print("  600s = 10 minutes")
                print("  1800s = 30 minutes")
                print("  3600s = 1 hour")
                
                interval_str = input_styled("Forward interval (seconds)", str(current_interval))
                try:
                    interval = int(interval_str)
                    if interval > 0:
                        rule['interval'] = interval
                        print_success(f"\nInterval set to {interval}s ({interval // 60} minutes)")
                    else:
                        print_error("\nInterval must be positive!")
                except ValueError:
                    print_error("\nInvalid interval value!")
                time.sleep(1)
            elif key == '+' or key == '=':  # Increase interval by 60s
                rule = rules[current_idx]
                current_interval = rule.get('interval', 60)
                rule['interval'] = current_interval + 60
            elif key == '-':  # Decrease interval by 60s
                rule = rules[current_idx]
                current_interval = rule.get('interval', 60)
                new_interval = current_interval - 60
                if new_interval >= 60:
                    rule['interval'] = new_interval
            elif key == 'ESC':
                # Save and exit
                try:
                    with open(rules_file, 'w') as f:
                        yaml.dump(rules_data, f, default_flow_style=False, sort_keys=False)
                    print_success(f"\n✓ Saved to {rules_file}")
                    print_info("\nRestart nettemp_client to apply changes")
                    time.sleep(2)
                except Exception as e:
                    print_error(f"\nFailed to save: {e}")
                    time.sleep(2)
                break
    
    def _mqtt_autodiscover_devices(self):
        """Interactive MQTT device autodiscovery with selection interface"""
        clear_screen()
        print_header("MQTT DEVICE AUTODISCOVERY")
        
        # Check MQTT configuration
        mqtt_cfg = self.config.get('mqtt', {})
        if not mqtt_cfg.get('enabled'):
            print_warning("\nMQTT Bridge is not enabled!")
            print_info("Enable MQTT Bridge first, then run autodiscovery.")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        broker = mqtt_cfg.get('broker', '')
        port = mqtt_cfg.get('port', 1883)
        username = mqtt_cfg.get('username')
        password = mqtt_cfg.get('password')
        use_tls = mqtt_cfg.get('tls', False)
        
        if not broker:
            print_error("\nNo MQTT broker configured!")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        print(f"\n{Colors.BOLD}This will discover all MQTT devices broadcasting to:{Colors.ENDC}")
        print(f"  Broker: {Colors.CYAN}{broker}:{port}{Colors.ENDC}")
        print(f"\n{Colors.YELLOW}Press Ctrl+C to stop discovery and select devices{Colors.ENDC}\n")
        
        time.sleep(2)
        
        try:
            import paho.mqtt.client as mqtt_client
        except ImportError:
            print_error("\npaho-mqtt not installed!")
            print_info("Install with: pip install paho-mqtt")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        # Dictionary to store discovered devices: {device_key: device_info}
        discovered_devices = {}
        message_count = 0
        
        # Load topics from log file if exists
        topic_log_file = get_data_dir()
        topic_log_file.mkdir(parents=True, exist_ok=True)
        topic_log_file = topic_log_file / 'mqtt_topics.log'
        logged_topics = set()
        logged_topics_count = 0
        if topic_log_file.exists():
            try:
                with open(topic_log_file, 'r') as f:
                    logged_topics = set(line.strip() for line in f if line.strip())
                logged_topics_count = len(logged_topics)
                print_info(f"Loaded {logged_topics_count} topics from previous runs")
            except Exception as e:
                pass

        # Deduplicate live discovery output (devices publish frequently).
        seen_topics = set(logged_topics)
        
        # Get currently subscribed topics
        current_subscribe_topics = mqtt_cfg.get('subscribe_topics', [])
        if isinstance(current_subscribe_topics, str):
            current_subscribe_topics = [current_subscribe_topics]
        # Keep all topics for subscription checking (including wildcards like ESP32_Easy_1/#)

        def is_topic_subscribed(topic: str) -> bool:
            """Check if a topic is already covered by current subscribe patterns"""
            for sub in current_subscribe_topics:
                if not sub:
                    continue
                if sub == topic:
                    return True
                if sub.endswith('/#'):
                    prefix = sub[:-2]
                    if topic.startswith(prefix):
                        return True
            return False

        def add_topic(entry: dict, topic: str):
            """Ensure topic is tracked in entry (primary topic stored as 'topic')."""
            if not topic:
                return
            topics = entry.setdefault('topics', [])
            if topic not in topics:
                topics.append(topic)
                topics.sort()
            if not entry.get('topic'):
                entry['topic'] = topics[0]

        def merge_device(store: dict, device_key: str, base_info: dict, topic: str, sensors: list[str]):
            """Merge device info into store keyed by device_key, tracking topics and sensors."""
            if device_key in store:
                entry = store[device_key]
                # Update human-friendly fields if we have better info
                for field in ['name', 'brand', 'model', 'mac', 'type']:
                    if base_info.get(field) and base_info.get(field) != 'unknown':
                        entry[field] = base_info[field]
                # Merge sensors
                if sensors:
                    entry.setdefault('sensors', [])
                    for s in sensors:
                        if s not in entry['sensors']:
                            entry['sensors'].append(s)
                    entry['sensors'].sort()
                add_topic(entry, topic)
                entry['subscribed'] = base_info.get('subscribed', entry.get('subscribed', False))
                entry['from_log'] = entry.get('from_log', base_info.get('from_log', False))
            else:
                new_entry = {
                    'mac': base_info.get('mac', ''),
                    'name': base_info.get('name', 'unknown'),
                    'type': base_info.get('type', 'MQTT'),
                    'brand': base_info.get('brand', 'unknown'),
                    'model': base_info.get('model', 'unknown'),
                    'sensors': sensors.copy() if sensors else [],
                    'topic': topic,
                    'topics': [],
                    'subscribed': base_info.get('subscribed', False),
                    'from_log': base_info.get('from_log', False)
                }
                add_topic(new_entry, topic)
                store[device_key] = new_entry

        # Parse logged topics before live discovery so user can see them immediately
        logged_devices = {}
        if logged_topics:
            print_info("Parsing logged topics from previous runs...")
            for topic in logged_topics:
                # Skip exclude patterns
                if any(excluded in topic for excluded in ['LWT', '/status/', 'homeassistant/', 'config']):
                    continue

                # Parse Theengs Gateway topics: home/TheengsGateway/BTtoMQTT/A4C138165B5D
                if 'BTtoMQTT' in topic:
                    parts = topic.split('/')
                    if len(parts) >= 4:
                        mac_normalized = parts[-1]
                        # Format MAC with colons
                        if len(mac_normalized) == 12 and mac_normalized.isalnum():
                            mac_formatted = ':'.join([mac_normalized[i:i+2] for i in range(0, 12, 2)])
                            device_key = f"ble_{mac_normalized}"

                            device_topic = topic
                            is_subscribed = is_topic_subscribed(device_topic)

                            merge_device(
                                logged_devices,
                                device_key,
                                {
                                    'mac': mac_formatted,
                                    'name': f'BLE-{mac_normalized[-6:]}',
                                    'type': 'BLE',
                                    'brand': 'Theengs',
                                    'model': 'From Log',
                                    'subscribed': is_subscribed,
                                    'from_log': True,
                                },
                                device_topic,
                                sensors=[]
                            )

                # Parse ESPEasy/Tasmota/Other device topics: ESP32_Easy_1/BMP280/temperature
                elif '/' in topic:
                    parts = topic.split('/')
                    if len(parts) >= 2:
                        device_name = parts[0]
                        sensor_path = '/'.join(parts[1:])
                        device_key = f"mqtt_{device_name}"

                        is_subscribed = is_topic_subscribed(topic) or is_topic_subscribed(f"{device_name}/#")
                        merge_device(
                            logged_devices,
                            device_key,
                            {
                                'mac': device_name,
                                'name': device_name,
                                'type': 'MQTT',
                                'brand': 'ESPEasy/Tasmota',
                                'model': 'From Log',
                                'subscribed': is_subscribed,
                                'from_log': True,
                            },
                            topic,
                            sensors=[sensor_path]
                        )

            if logged_devices:
                print_success(f"Found {len(logged_devices)} device(s) from log:")
                for dev in sorted(logged_devices.values(), key=lambda d: d.get('topic', '')):
                    sensors_str = ','.join(dev['sensors']) if dev['sensors'] else 'none'
                    sub_mark = f" {Colors.GREEN}[SUBSCRIBED]{Colors.ENDC}" if dev.get('subscribed') else f" {Colors.YELLOW}[LOG]{Colors.ENDC}"
                    print(f"  {Colors.GREEN}✓{Colors.ENDC} Log: {dev['name']} ({dev['mac']}) - {dev['brand']} {dev['model']} - Sensors: {sensors_str} - Topic: {dev['topic']}{sub_mark}")
                print()
        
        def on_connect(client, userdata, flags, rc, properties=None):
            if rc == 0:
                print_success(f"✓ Connected to {broker}:{port}")
                # Subscribe to common device topics
                client.subscribe("home/+/BTtoMQTT/+")  # Theengs Gateway
                client.subscribe("+/+/+")  # ESPEasy, Tasmota, etc.
                print_info("Listening for MQTT devices... (Press Ctrl+C when done)\n")
            else:
                print_error(f"Connection failed with code {rc}")
        
        def on_message(client, userdata, msg, properties=None):
            nonlocal message_count
            try:
                payload = msg.payload.decode('utf-8')
                data = json.loads(payload)
                
                # Skip if data is not a dictionary (e.g., numeric values)
                if not isinstance(data, dict):
                    return
                
                # Extract device info
                device_mac = data.get('id', 'unknown')
                device_name = data.get('name', 'unknown')
                device_type = data.get('type', 'unknown')
                brand = data.get('brand', 'unknown')
                model = data.get('model', 'unknown')
                device_topic = msg.topic

                # Get sensor fields
                metadata_fields = {'id', 'name', 'rssi', 'brand', 'model', 'model_id', 'type', 'mac', 'mfr', 'manufacturerdata'}
                sensor_fields = [k for k in data.keys() if k not in metadata_fields]
                
                # Create unique key using normalized MAC for BLE devices
                mac_normalized = device_mac.replace(':', '').upper()
                device_key = f"ble_{mac_normalized}"

                # If already in logged devices, just enrich and skip duplicate printing
                if device_key in logged_devices:
                    merge_device(
                        logged_devices,
                        device_key,
                        {
                            'mac': device_mac,
                            'name': device_name,
                            'type': 'BLE',
                            'brand': brand,
                            'model': model,
                            'subscribed': is_topic_subscribed(device_topic),
                        },
                        device_topic,
                        sensor_fields
                    )
                    return
                if device_topic in logged_topics:
                    return

                # Add or update device
                is_subscribed = is_topic_subscribed(device_topic)
                merge_device(
                    discovered_devices,
                    device_key,
                    {
                        'mac': device_mac,
                        'name': device_name,
                        'type': 'BLE',
                        'brand': brand,
                        'model': model,
                        'subscribed': is_subscribed,
                    },
                    device_topic,
                    sensor_fields
                )

                # Show discovered device only once per topic
                if device_topic not in seen_topics:
                    seen_topics.add(device_topic)
                    sensors_str = ','.join(sensor_fields) if sensor_fields else 'none'
                    subscribed_mark = f" {Colors.GREEN}[SUBSCRIBED]{Colors.ENDC}" if is_subscribed else ""
                    print(f"{Colors.GREEN}✓{Colors.ENDC} Found: {Colors.CYAN}{device_name}{Colors.ENDC} ({device_mac}) - {brand} {model} - Sensors: {sensors_str} - Topic: {device_topic}{subscribed_mark}")
                    message_count += 1
                
            except json.JSONDecodeError:
                # Silently skip non-JSON payloads
                pass
            except Exception as e:
                # Silently skip any other errors during discovery
                pass
        
        # Create MQTT client with API version compatibility
        try:
            # Try VERSION2 first (current), fallback to VERSION1, then old API
            try:
                client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, f"nettemp_discovery_{os.getpid()}")
            except (AttributeError, ValueError):
                client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, f"nettemp_discovery_{os.getpid()}")
        except (AttributeError, TypeError):
            # Fallback to old API (v1.x)
            client = mqtt_client.Client(f"nettemp_discovery_{os.getpid()}")
        
        if username and password:
            client.username_pw_set(username, password)
        
        if use_tls:
            import ssl
            client.tls_set(cert_reqs=ssl.CERT_NONE)
            client.tls_insecure_set(True)
        
        client.on_connect = on_connect
        client.on_message = on_message
        
        try:
            # Connect and start loop
            client.connect(broker, port, 60)
            client.loop_start()
            
            # Wait for user to press Ctrl+C
            while True:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Discovery stopped{Colors.ENDC}")
            print(f"Found {len(discovered_devices)} device(s) from live discovery\n")
        except Exception as e:
            print_error(f"\nConnection error: {e}")
            print_warning("Check broker/port, credentials, and TLS settings. Ensure broker is reachable from this host.")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        finally:
            client.loop_stop()
            client.disconnect()
        
        # Merge logged devices with discovered devices
        # Merge logged and discovered, preferring discovered to overwrite fields
        all_devices = {**logged_devices, **discovered_devices}
        # If same key in both, merge topics/sensors
        for key, dev in discovered_devices.items():
            if key in logged_devices:
                merge_device(all_devices, key, dev, dev.get('topic', ''), dev.get('sensors', []))

        if not all_devices:
            print_warning("\nNo devices found in discovery or logs!")
            print_info("Run nettemp_client.py first to populate mqtt_topics.log")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        print_success(f"✓ Total: {len(all_devices)} unique device(s) ({len(discovered_devices)} live, {len(logged_devices)} from log)\n")
        
        # Interactive selection
        time.sleep(1)
        clear_screen()
        print_header("SELECT DEVICES TO SUBSCRIBE")
        
        devices_list = sorted(all_devices.values(), key=lambda d: d.get('topic', ''))
        # Pre-select already subscribed devices
        selected = [device.get('subscribed', False) for device in devices_list]
        current_idx = 0
        
        while True:
            clear_screen()
            print_header("SELECT DEVICES TO SUBSCRIBE")
            if logged_topics_count:
                print_info(f"Loaded {logged_topics_count} topics from previous runs\n")
            
            print(f"\n{Colors.BOLD}Use ↑↓ arrows to navigate, SPACE to select/deselect, Enter to confirm{Colors.ENDC}\n")
            print(f"Found {len(devices_list)} device(s):\n")
            
            for idx, device in enumerate(devices_list):
                checkbox = "☑" if selected[idx] else "☐"
                sensors_str = ','.join(device['sensors']) if device['sensors'] else 'none'
                
                # Build status indicators
                status_parts = []
                if device.get('subscribed', False):
                    status_parts.append(f"{Colors.GREEN}[SUBSCRIBED]{Colors.ENDC}")
                if device.get('from_log', False):
                    status_parts.append(f"{Colors.YELLOW}[FROM LOG]{Colors.ENDC}")
                status_mark = ' ' + ' '.join(status_parts) if status_parts else ""
                
                if idx == current_idx:
                    print(f"{Colors.LIGHT_BLUE}▶ {checkbox} {device['name']} ({device['mac']}) - {device['brand']} {device['model']} - {device['topic']}{status_mark}")
                    print(f"    Sensors: {sensors_str}{Colors.ENDC}")
                else:
                    print(f"  {checkbox} {device['name']} ({device['mac']}) - {device['brand']} {device['model']} - {device['topic']}{status_mark}")
                    if idx == current_idx - 1 or idx == current_idx + 1:
                        print(f"    Sensors: {sensors_str}")
            
            total_selected = sum(selected)
            new_selected = sum(1 for i, sel in enumerate(selected) if sel and not devices_list[i].get('subscribed'))
            already_subscribed = total_selected - new_selected
            print(f"\n{Colors.GREEN}Selected: {total_selected} device(s){Colors.ENDC} ({new_selected} new, {already_subscribed} already subscribed)")
            
            key = get_key()
            
            if key == '':
                continue
            elif key == 'UP':
                current_idx = (current_idx - 1) % len(devices_list)
            elif key == 'DOWN':
                current_idx = (current_idx + 1) % len(devices_list)
            elif key == ' ':  # Space to toggle
                selected[current_idx] = not selected[current_idx]
            elif key == '\r' or key == '\n':  # Enter to confirm
                break
            elif key == 'ESC':
                print_info("\nAutodiscovery cancelled")
                time.sleep(1)
                return
        
        # Get selected devices
        selected_devices = [devices_list[i] for i, sel in enumerate(selected) if sel]

        if not selected_devices:
            print_warning("\nNo devices selected!")
            time.sleep(1)
            return
        
        # Update config.conf subscribe_topics
        clear_screen()
        print_header("UPDATING MQTT SUBSCRIPTION")
        
        print(f"\n{Colors.BOLD}Adding {len(selected_devices)} device(s) to MQTT subscribe_topics...{Colors.ENDC}\n")
        
        try:
            # Build list of device-specific topics (use all known topics from discovery/log)
            device_topics = []
            for d in selected_devices:
                topics = d.get('topics') or []
                if not topics and d.get('topic'):
                    topics = [d['topic']]
                for t in topics:
                    if t:
                        device_topics.append(t)

            # Track identifiers to drop old topics for the same device
            selected_ble_macs = set()
            selected_mqtt_prefixes = set()
            for d in selected_devices:
                if d.get('type') == 'BLE' and d.get('mac'):
                    selected_ble_macs.add(d['mac'].replace(':', '').upper())
                elif d.get('type') == 'MQTT' and d.get('topic'):
                    # prefix before first slash
                    base = d['topic'].split('/')[0]
                    selected_mqtt_prefixes.add(base)
            
            # Get current subscribe_topics from config
            if 'mqtt' not in self.config:
                self.config['mqtt'] = {}
            
            current_topics = self.config['mqtt'].get('subscribe_topics', [])
            if isinstance(current_topics, str):
                current_topics = [current_topics]
            elif not isinstance(current_topics, list):
                current_topics = []
            
            # Remove old device topics for selected devices
            filtered_topics = []
            for t in current_topics:
                if t == '#':
                    continue
                drop = False
                # Drop old BLE topics for selected MACs
                for mac in selected_ble_macs:
                    if t.upper().endswith(mac):
                        drop = True
                        break
                # Drop old MQTT device topics for selected prefixes
                if not drop:
                    for prefix in selected_mqtt_prefixes:
                        if t.startswith(prefix + "/") or t.startswith(prefix + "/#"):
                            drop = True
                            break
                if not drop:
                    filtered_topics.append(t)
            
            # Add new topics and deduplicate
            filtered_topics.extend(device_topics)
            filtered_topics = sorted(set(filtered_topics))  # Sort and deduplicate
            
            # Update config
            self.config['mqtt']['subscribe_topics'] = filtered_topics
            
            # Save config
            self.save_main_config()
            
            print_success("✓ Subscribe topics updated in config.conf\n")
            print(f"{Colors.BOLD}Subscribed to devices:{Colors.ENDC}")
            for device in sorted(selected_devices, key=lambda d: (d.get('topic') or '', d.get('name') or '')):
                sensors_str = ','.join(device['sensors']) if device['sensors'] else 'none'
                topics_show = device.get('topics') or ([device['topic']] if device.get('topic') else [])
                print(f"  • {Colors.CYAN}{device['name']}{Colors.ENDC} ({device['mac']})")
                print(f"    {device['brand']} {device['model']} - Sensors: {sensors_str}")
                print(f"    {Colors.LIGHT_BLUE}Topics:{Colors.ENDC} {', '.join(topics_show)}")
            
            print(f"\n{Colors.YELLOW}Restart nettemp client to apply changes{Colors.ENDC}")
            
            restart = input_styled("\nRestart nettemp client now? (y/n)", "y")
            if restart.lower() in ['y', 'yes']:
                self._restart_client()
            
        except Exception as e:
            print_error(f"\nFailed to update config.conf: {e}")
            import traceback
            traceback.print_exc()
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def check_mqtt_broker_connection(self, broker: str, port: int, username: str = None, password: str = None, tls: bool = False) -> tuple[bool, str]:
        """Test connection to MQTT broker. Returns (success, message)"""
        try:
            # Try importing paho-mqtt
            try:
                import paho.mqtt.client as mqtt_client
            except ImportError:
                return False, "paho-mqtt not installed (run: pip install paho-mqtt)"
            
            connected = False
            error_msg = ""
            
            def on_connect(client, userdata, flags, rc):
                nonlocal connected, error_msg
                if rc == 0:
                    connected = True
                else:
                    error_codes = {
                        1: 'Connection refused - incorrect protocol version',
                        2: 'Connection refused - invalid client identifier',
                        3: 'Connection refused - server unavailable',
                        4: 'Connection refused - bad username or password',
                        5: 'Connection refused - not authorized'
                    }
                    error_msg = error_codes.get(rc, f'Connection failed with code {rc}')
            
            # Create client
            client = mqtt_client.Client(client_id="nettemp_config_test")
            client.on_connect = on_connect
            
            # Set authentication if provided
            if username:
                client.username_pw_set(username, password)
            
            # Set TLS if enabled
            if tls:
                client.tls_set()
            
            # Try to connect (non-blocking)
            try:
                client.connect_async(broker, port, 5)
                client.loop_start()
                
                # Wait up to 5 seconds for connection
                import time
                for _ in range(50):  # 5 seconds total
                    if connected:
                        break
                    time.sleep(0.1)
                
                client.loop_stop()
                client.disconnect()
                
                if connected:
                    return True, f"Successfully connected to {broker}:{port}"
                else:
                    return False, error_msg or f"Connection timeout to {broker}:{port}"
                    
            except Exception as e:
                return False, f"Connection error: {str(e)}"
                
        except Exception as e:
            return False, f"Test failed: {str(e)}"
    
    def check_background_process(self) -> Optional[int]:
        """Check if nettemp_client.py is running in background. Returns PID if found."""
        try:
            # Check for PID file first
            pidfile = get_pidfile()
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
            
            # If no pidfile, search for running python process (module or script form)
            for pattern in ['nettemp.nettemp_client', 'nettemp_client.py']:
                result = subprocess.run(
                    ['pgrep', '-f', pattern],
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
    
    def _restart_client(self):
        """Restart nettemp client to apply configuration changes"""
        try:
            pid = self.check_background_process()
            
            if pid:
                print_info(f"\nStopping background client (PID: {pid})...")
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(2)
                    print_success("✓ Client stopped")
                except Exception as e:
                    print_error(f"Failed to stop client: {e}")
                    return
            
            print_info("Starting client in background...")
            try:
                # Start client in background
                env = os.environ.copy()
                env['NETTEMP_CLIENT_BG'] = '1'
                env["NETTEMP_CONFIG_DIR"] = str(self.config_dir)

                log_dir = get_data_dir()
                log_dir.mkdir(parents=True, exist_ok=True)
                log_file = log_dir / "nettemp_client.log"
                with open(log_file, "ab") as lf:
                    subprocess.Popen(
                        [sys.executable, "-m", "nettemp.nettemp_client"],
                        stdin=subprocess.DEVNULL,
                        stdout=lf,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                        env=env,
                    )
                
                time.sleep(2)
                new_pid = self.check_background_process()
                if new_pid:
                    print_success(f"✓ Client started (PID: {new_pid})")
                    print_info(f"Logs: {log_file}")
                else:
                    print_warning("Client may still be starting...")
            except Exception as e:
                print_error(f"Failed to start client: {e}")
        except Exception as e:
            print_error(f"Failed to restart client: {e}")
        
        time.sleep(2)
    
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
            
            config_file = self.config_file
            example_config = self.base_path / 'example_config.conf'
            
            if config_file.exists() and example_config.exists():
                print_success("config.conf preserved")
                print_info("Note: Check example_config.conf for new options")
            
            drivers_file = self.drivers_file
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
    
    def setup_bluetooth_sudoers(self):
        """Setup sudoers for passwordless Bluetooth management"""
        try:
            # Check if btmgmt is available
            btmgmt_path = subprocess.run(['which', 'btmgmt'], capture_output=True, text=True).stdout.strip()
            if not btmgmt_path:
                return False
            
            # Check if already configured
            sudoers_file = "/etc/sudoers.d/nettemp-bluetooth"
            check_cmd = f"sudo test -f {sudoers_file}"
            result = subprocess.run(check_cmd, shell=True, capture_output=True)
            
            if result.returncode == 0:
                return True  # Already configured
            
            # Get current user
            current_user = os.getenv('USER')
            
            # Create sudoers content
            sudoers_content = f"""# Allow Nettemp client to manage Bluetooth without password
# Created by nettemp_config.py
{current_user} ALL=(ALL) NOPASSWD: {btmgmt_path}
"""
            
            # Check for hciconfig as fallback
            hciconfig_path = subprocess.run(['which', 'hciconfig'], capture_output=True, text=True).stdout.strip()
            if hciconfig_path:
                sudoers_content += f"{current_user} ALL=(ALL) NOPASSWD: {hciconfig_path}\n"
            
            # Create temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sudoers') as f:
                f.write(sudoers_content)
                temp_file = f.name
            
            # Validate syntax
            validate_cmd = f"sudo visudo -c -f {temp_file}"
            result = subprocess.run(validate_cmd, shell=True, capture_output=True)
            
            if result.returncode != 0:
                os.unlink(temp_file)
                return False
            
            # Install sudoers file
            install_cmd = f"sudo cp {temp_file} {sudoers_file} && sudo chmod 0440 {sudoers_file} && sudo chown root:root {sudoers_file}"
            result = subprocess.run(install_cmd, shell=True, capture_output=True)
            os.unlink(temp_file)
            
            return result.returncode == 0
            
        except Exception as e:
            print_error(f"Failed to setup Bluetooth sudoers: {e}")
            return False

    def setup_cron_job(self):
        """Setup cron job for auto-start on boot"""
        clear_screen()
        print_header("Setup Auto-Start (Cron Job)")

        # Check and setup Bluetooth sudoers for LYWSD03MMC driver
        print_info("Checking Bluetooth permissions for BLE sensors...")
        if self.setup_bluetooth_sudoers():
            print_success("✓ Bluetooth sudoers configured (passwordless btmgmt)")
        else:
            print_warning("⚠ Could not setup Bluetooth sudoers (BLE sensors may need manual reset)")
        print()

        # Check if already configured
        if self.check_cron_status():
            print_warning("Cron job already configured!")
            print_info("Current cron jobs:")
            try:
                for line in get_nettemp_cron_status().lines:
                    print(f"  {line}")
            except Exception:
                pass
            print()
            overwrite = input_styled("Replace existing cron job? (y/n)", "n")
            if overwrite.lower() != 'y':
                input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
                return

        # Prefer local venv if present; otherwise use the current interpreter (pipx/installed package).
        venv_python = self.base_path / 'venv' / 'bin' / 'python3'
        python_cmd = venv_python if venv_python.exists() else Path(sys.executable)
        if not python_cmd.exists():
            print_error("Python interpreter not found!")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return

        cron_entry = build_nettemp_reboot_entry(str(python_cmd), config_dir=str(self.config_dir))

        print_info("Will add the following cron job:")
        print(f"  {cron_entry}\n")
        print_info("This will start the client 30 seconds after system boot.\n")

        confirm = input_styled("Add this cron job? (y/n)", "y")
        if confirm.lower() != 'y':
            return

        try:
            install_or_replace_nettemp_cron(str(python_cmd), config_dir=str(self.config_dir))
        except Exception as e:
            print_error(f"Failed to setup cron job: {e}")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return

        print_success("Cron job added successfully!")
        print_info("The client will now start automatically on system boot.")

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
            for line in get_nettemp_cron_status().lines:
                print(f"  {line}")
        except Exception:
            pass

        print()
        confirm = input_styled("Remove nettemp cron job? (y/n)", "n")
        if confirm.lower() != 'y':
            return

        try:
            removed = remove_all_nettemp_cron()
            if removed:
                print_success("Cron job removed successfully!")
            else:
                print_info("No nettemp cron job found.")
        except Exception as e:
            print_error(f"Failed to remove cron job: {e}")

        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def start_background_client(self):
        """Start nettemp_client.py in background"""
        # Check if drivers_config.yaml exists, if not copy from example
        drivers_config_file = self.drivers_file
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
        
        try:
            env = os.environ.copy()
            env['NETTEMP_CLIENT_BG'] = '1'
            env["NETTEMP_CONFIG_DIR"] = str(self.config_dir)

            log_dir = get_data_dir()
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "nettemp_client.log"

            # Prefer current interpreter (pipx/venv) to ensure installed package is available.
            with open(log_file, "ab") as lf:
                process = subprocess.Popen(
                    [sys.executable, "-m", "nettemp.nettemp_client"],
                    stdin=subprocess.DEVNULL,
                    stdout=lf,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=env,
                )
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if it's still running
            if process.poll() is None:
                print_success(f"Client started in background (PID: {process.pid})")
                print_info(f"Logs: {log_file}")
            else:
                print_error("Client failed to start.")
                print_info(f"Logs: {log_file}")
                try:
                    tail = log_file.read_text(errors="replace").splitlines()[-30:]
                    if tail:
                        print("\nLast log lines:")
                        for line in tail:
                            print(f"  {line}")
                except Exception:
                    pass
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
                if current_option == 0:  # Setup Auto-Start
                    self.setup_cron_job()
                elif current_option == 1:  # Remove Auto-Start
                    self.remove_cron_job()
                elif current_option == 2:  # View Cron
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
                elif current_option == 3:  # Start Background
                    self.start_background_client()
                elif current_option == 4:  # Stop Background
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
                elif current_option == 5:  # Back
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

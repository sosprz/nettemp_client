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
            print("✓ Required packages installed")
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
    
    print("✅ Environment ready!\n")

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
        
        if key == 'UP':
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
        0x23: "BH1750 (Light sensor)",
        0x29: "TSL2561/VL53L0X",
        0x39: "TSL2561 (Light sensor)",
        0x40: "HTU21D (Humidity sensor)",
        0x48: "TMP102 (Temperature)",
        0x49: "TMP102 (Temperature, alt)",
        0x60: "MPL3115A2 (Pressure/Altitude)",
        0x68: "DS1307/MPU6050",
        0x76: "BMP180/BME280 (Pressure/Temp)",
        0x77: "BMP180/BME280 (Pressure/Temp, alt)",
        0x18: "DS2482 (1-Wire bridge)",
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
                "Discover Devices (I2C + 1-Wire)",
                "Test & View Readings",
                "Test Connectivity & Send Data",
                "System Management (Setup/Update/Cron/Background)",
                "Save Configuration",
                "Exit"
            ]
            
            for idx, option in enumerate(menu_options):
                if idx == current_option:
                    print(f"{Colors.LIGHT_BLUE}▶ {option}{Colors.ENDC}")
                else:
                    print(f"  {option}")
            
            print(f"\n{Colors.LIGHT_BLUE}Use ↑↓ arrows, Enter to select, Esc to exit{Colors.ENDC}")
            
            key = get_key()
            
            if key == 'UP':
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
                    self.save_main_config()
                    self.save_drivers_config()
                    input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
                elif current_option == 9:
                    clear_screen()
                    print_success("Configuration saved! You can now run:")
                    print(f"  {Colors.BOLD}python3 nettemp_client.py{Colors.ENDC}")
                    break
            elif key == 'ESC':
                clear_screen()
                print_success("Configuration saved! You can now run:")
                print(f"  {Colors.BOLD}python3 nettemp_client.py{Colors.ENDC}")
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
        else:
            print_info("Cancelled")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def configure_http_bridge(self):
        """Configure HTTP Bridge settings"""
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
            print(f"Current status: {Colors.GREEN}Enabled{Colors.ENDC}")
            print(f"  Host: {current_host}")
            print(f"  Port: {current_port}")
            if current_token:
                print(f"  Auth token: {current_token[:8]}...")
        else:
            print(f"Current status: {Colors.YELLOW}Disabled{Colors.ENDC}")
        
        print()
        
        # Configure
        enabled_str = input_styled("Enable HTTP Bridge? (y/n)", "y" if current_enabled else "n")
        enabled = enabled_str.lower() in ['y', 'yes']
        
        if enabled:
            host = input_styled("Listen host (0.0.0.0 = all interfaces)", str(current_host))
            port_str = input_styled("Listen port", str(current_port))
            try:
                port = int(port_str)
            except:
                port = current_port
            
            auth_token = input_styled("Auth token (optional, for basic security)", current_token)
            
            self.config['http_bridge'] = {
                'enabled': True,
                'host': host,
                'port': port,
            }
            
            if auth_token:
                self.config['http_bridge']['auth_token'] = auth_token
            
            print_success(f"\nHTTP Bridge enabled on {host}:{port}")
            if auth_token:
                print_info("Clients must include header: Authorization: Bearer <token>")
        else:
            self.config['http_bridge'] = {'enabled': False}
            print_info("\nHTTP Bridge disabled")
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
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
        
        # Build detection map
        detected_drivers = {}
        suggestions = self._suggest_drivers_from_i2c(i2c_devices)
        for driver, reason in suggestions.items():
            detected_drivers[driver] = reason
        
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
            'GPIO Sensors': ['dht11', 'dht22'],
            'Other': ['ping', 'sdm120', 'vl53l0x', 'adxl345', 'mpl3115a2']
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
                enabled = self.drivers_config[current_driver].get('enabled', False)
                interval = self.drivers_config[current_driver].get('read_in_sec', 60)
                interval_min = interval / 60
                
                print(f"\n{Colors.BOLD}Selected: {current_driver}{Colors.ENDC}")
                status_text = f"{Colors.GREEN}ENABLED{Colors.ENDC}" if enabled else f"{Colors.RED}DISABLED{Colors.ENDC}"
                print(f"Status: {status_text}")
                print(f"Interval: {interval}s ({interval_min:.1f} min)")
                
                # Show detection status
                if current_driver in detected_drivers:
                    print(f"Hardware: {Colors.GREEN}✓ {detected_drivers[current_driver]}{Colors.ENDC}")
                else:
                    print(f"Hardware: {Colors.YELLOW}? Not detected{Colors.ENDC}")
                print()
            
            print("─" * 70 + "\n")
            
            # Display all drivers
            for idx, driver in enumerate(all_drivers):
                enabled = self.drivers_config[driver].get('enabled', False)
                interval = self.drivers_config[driver].get('read_in_sec', 60)
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
            
            print(f"\n{Colors.LIGHT_BLUE}↑↓: Navigate | Space: Toggle | +/-: Change interval | Esc: Back{Colors.ENDC}")
            print(f"{Colors.GREEN}[HW]{Colors.ENDC} = Hardware detected")
            
            key = get_key()
            
            if key == 'UP':
                current_idx = (current_idx - 1) % len(all_drivers)
            elif key == 'DOWN':
                current_idx = (current_idx + 1) % len(all_drivers)
            elif key == ' ':  # Space to toggle
                driver = all_drivers[current_idx]
                current_state = self.drivers_config[driver].get('enabled', False)
                self.drivers_config[driver]['enabled'] = not current_state
            elif key == '+' or key == '=':  # Increase interval
                driver = all_drivers[current_idx]
                current_interval = self.drivers_config[driver].get('read_in_sec', 60)
                self.drivers_config[driver]['read_in_sec'] = current_interval + 10
            elif key == '-':  # Decrease interval
                driver = all_drivers[current_idx]
                current_interval = self.drivers_config[driver].get('read_in_sec', 60)
                if current_interval > 10:
                    self.drivers_config[driver]['read_in_sec'] = current_interval - 10
            elif key == 'ESC':
                break
    
    def discover_devices(self):
        """Discover I2C and 1-Wire devices"""
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
        
        input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
    
    def _suggest_drivers_from_i2c(self, devices: List[Dict]) -> Dict[str, str]:
        """Suggest drivers based on detected I2C devices"""
        suggestions = {}
        
        for device in devices:
            addr = device['address']
            
            if addr in ['0x76', '0x77'] and 'BME280' in device['name']:
                suggestions['bme280'] = f"Detected at {addr}"
            elif addr in ['0x76', '0x77'] and 'BMP180' in device['name']:
                suggestions['bmp180'] = f"Detected at {addr}"
            elif addr == '0x23':
                suggestions['bh1750'] = f"Detected at {addr}"
            elif addr in ['0x29', '0x39']:
                suggestions['tsl2561'] = f"Detected at {addr}"
            elif addr == '0x40':
                suggestions['htu21d'] = f"Detected at {addr}"
            elif addr in ['0x48', '0x49']:
                suggestions['tmp102'] = f"Detected at {addr}"
            elif addr == '0x60':
                suggestions['mpl3115a2'] = f"Detected at {addr}"
            elif addr == '0x18':
                suggestions['w1_kernel'] = f"DS2482 1-Wire bridge detected at {addr}"
        
        return suggestions
    
    def test_readings(self):
        """Test configuration and show live readings"""
        clear_screen()
        print_header("TEST READINGS")
        
        print_info("Testing sensor readings with current configuration...")
        print_warning("Press Ctrl+C to stop\n")
        
        # Import driver loader
        try:
            sys.path.insert(0, str(self.base_path))
            from driver_loader import DriverLoader
            
            loader = DriverLoader(config_file=str(self.drivers_file))
            
            try:
                while True:
                    print(f"\n{Colors.BOLD}[{time.strftime('%H:%M:%S')}]{Colors.ENDC}")
                    
                    for driver_name, driver_config in self.drivers_config.items():
                        if not isinstance(driver_config, dict):
                            continue
                        
                        if driver_config.get('enabled'):
                            try:
                                readings = loader.run_driver(driver_name, driver_config)
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
                        if 'nettemp_client' in line:
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
        
        client_script = self.base_path / 'nettemp_client.py'
        if not client_script.exists():
            print_error("nettemp_client.py not found!")
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")
            return
        
        # Create cron entry
        cron_entry = f"@reboot /bin/sleep 30 && {venv_python} {client_script} &"
        
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
                                              if line and 'nettemp_client' not in line])
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
                "Run Setup Script (setup.sh)",
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
            
            if key == 'UP':
                current_option = (current_option - 1) % len(menu_options)
            elif key == 'DOWN':
                current_option = (current_option + 1) % len(menu_options)
            elif key == '\r' or key == '\n':  # Enter
                if current_option == 0:  # Run Setup
                    self.run_setup_script()
                elif current_option == 1:  # Run Update
                    self.run_update_script()
                elif current_option == 2:  # Setup Auto-Start
                    self.setup_cron_job()
                elif current_option == 3:  # Remove Auto-Start
                    self.remove_cron_job()
                elif current_option == 4:  # View Cron
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
                elif current_option == 5:  # Start Background
                    self.start_background_client()
                elif current_option == 6:  # Stop Background
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
                elif current_option == 7:  # Back
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

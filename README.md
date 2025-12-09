# Nettemp Client

IoT sensor client for Raspberry Pi and other Linux devices. Reads sensors and sends data to **Nettemp Cloud** or **self-hosted Nettemp** instance.

**☁️ Cloud** - Managed hosting at [nettemp.pl](https://nettemp.pl) *(Available Now!)*  
**🐳 Docker** - Self-hosted with Docker Compose *(Available Now)*  
**🏠 Self-Hosted** - Deploy to your own server/VPS *(Available Now)*

## Deployment Options

### ☁️ Nettemp Cloud - **nettemp.pl** *(Recommended)*
**Fully managed service** - Production ready and hosted on Cloudflare Workers.

- ✅ **Zero infrastructure** - No servers to maintain
- ✅ **Instant setup** - Get API key and start sending data
- ✅ **Global edge network** - Low latency worldwide
- ✅ **Automatic scaling** - Handles any number of devices
- ✅ **Web dashboard** - View and analyze sensor data
- ✅ **Free tier available** - Perfect for hobby projects

**Get started:** Visit [https://nettemp.pl](https://nettemp.pl), create account, copy your API key.

### 🏠 Self-Hosted *(Full Control)*
Run your own Nettemp server - available as Docker containers or manual deployment.

- ✅ **Complete control** - Your data, your infrastructure
- ✅ **Docker support** - One-command setup with `docker-compose up -d`
- ✅ **LAN-only option** - Works offline/isolated networks
- ✅ **Any platform** - Linux, Windows, cloud providers, Raspberry Pi
- ✅ **Custom domains** - Use your own URLs

**Repository:** [github.com/sosprz/nettemp](https://github.com/sosprz/nettemp) (includes Docker Compose setup)  
**Docker Hub:** [przemeksdocker/nettemp](https://hub.docker.com/r/przemeksdocker/nettemp)

---

**This client works with both options** - just configure the server URL and API key!

## Features

- ⚡ **22+ sensor drivers** - Temperature, humidity, light, motion, network, power
- 🔄 **Auto-discovery** - Automatically detects connected sensors
- ⏱️ **Scheduled reading** - Configurable intervals per sensor
- ☁️ **Cloud sync** - Real-time data to Nettemp Cloud
- 🔧 **Easy config** - YAML-based sensor configuration
- 🚀 **Auto-start** - Runs on boot via cron
- 🔌 **I2C/GPIO/1-Wire** - Full hardware support
- 📊 **System monitoring** - CPU, RAM, temperature

## Quick Install

**On Raspberry Pi / Linux device:**

```bash
# 1. Clone repository
git clone https://github.com/sosprz/nettemp_client.git
cd nettemp_client

# 2. Run interactive configuration (auto-installs everything)
python3 nettemp_config.py
```

<div align="center">
<img src="img/nt_client_menu.png" alt="Configuration Menu" width="400" />
<img src="img/nt_client_driver.png" alt="Driver Configuration" width="400" />
<img src="img/nt_client_discovery.png" alt="I2C Device Scanner" width="400" />
<img src="img/nt_client_test.png" alt="Test Sensor Readings" width="400" />
</div>

That's it! The configuration tool will:
- ✅ Auto-install Python, venv, and system packages
- ✅ Create virtual environment
- ✅ Install Python dependencies
- ✅ Interactively configure servers and sensors
- ✅ Discover connected devices (I2C + 1-Wire)
- ✅ Test connectivity
- ✅ Setup auto-start on boot (cron)
- ✅ Start client in background

### Manual Configuration

If you prefer to edit config files directly:

```bash
# Copy example configs
cp example_config.conf config.conf
cp example_drivers_config.yaml drivers_config.yaml

# Edit configs
nano config.conf         # Set your server URL and API key
nano drivers_config.yaml # Enable sensors you have

# Run the client
python3 nettemp_client.py
```

## Available Drivers

<div align="center">
<img src="img/nettemp-raspi.jpg" alt="Nettemp Raspberry Pi HAT" width="360" style="margin:8px" />
<img src="img/nettemp-sensors1.jpg" alt="Nettemp sensors" width="360" style="margin:8px" />
</div>

The client supports **22+ sensor drivers** with automatic hardware detection and configuration:

### System Monitoring
- `system` - CPU usage, RAM usage, disk space
- `rpi` - Raspberry Pi CPU temperature (reads from /sys/class/thermal)
- `lm_sensors` - Linux hardware monitoring (CPU, GPU, fans, voltages)

### Temperature & Humidity Sensors

**1-Wire (DS18B20):**
- `w1_kernel` - Kernel-based 1-Wire sensors
  - Direct GPIO connection (default)
  - **DS2482 I2C-to-1Wire bridge** support (set `ds2482: true`)
  - Auto-discovers all connected DS18B20 sensors
  - Supports **Dallas Semiconductor DS9490R USB 1-Wire adapter**
- `w1_kernel_gpio` - Simplified GPIO-only DS18B20 driver

**GPIO Sensors:**
- `dht11` - DHT11 temperature/humidity sensor (GPIO)
- `dht22` - DHT22/AM2302 temperature/humidity sensor (GPIO, higher accuracy)

**BLE Sensors:**
- `lywsd03mmc` - Xiaomi Mi Temperature Humidity Sensor 2 (Bluetooth Low Energy)
  - Auto-connects to LYWSD03MMC sensors
  - Reports temperature and humidity
  - Supports multiple sensors via MAC address filtering

**I2C Sensors:**
- `tmp102` - High-accuracy temperature sensor (±0.5°C)
- `bme280` - Temperature, humidity, pressure (Bosch)
- `bmp180` - Temperature, pressure (Bosch, legacy)
- `htu21d` - Temperature, humidity (±2% RH)
- `hih6130` - Temperature, humidity (Honeywell)
- `mpl3115a2` - Temperature, pressure, altitude

### Light Sensors (I2C)
- `bh1750` - Ambient light sensor (0.5-100,000 lux)
- `tsl2561` - Light sensor with IR detection

### Motion & Acceleration (I2C)
- `adxl345` - 3-axis accelerometer, ±16g
- `adxl343` - 3-axis accelerometer (lower power version)

### Distance Sensors
- `vl53l0x` - Laser distance sensor, 30-1000mm (I2C)
- `hcsr04` - Ultrasonic distance sensor, 2-400cm (GPIO via trigger/echo pins)

### Analog Sensors (requires ADS1115 ADC)
- `capacitive_soil` - Capacitive soil moisture sensor v1.2
  - Requires ADS1115 16-bit ADC (I2C)
  - Reports 0-100% moisture and raw voltage
  - Calibration support (voltage_dry, voltage_wet)

### Network & Utilities
- `ping` - Network latency monitoring (multiple hosts)

### Power Monitoring (Modbus RTU)
- `sdm120` - Eastron SDM120 Modbus power meter
  - Measures AC voltage, current, active power
  - Modbus RTU over RS485 serial interface
  - Configurable baudrate (9600, 19200, 38400)
  - Configurable parity (N=None, E=Even, O=Odd)
  - Requires USB-to-RS485 adapter (e.g., /dev/ttyUSB0)
  - Reports: voltage (V), current (A), power (W)

## Running

### Interactive Configuration & Management
```bash
python3 nettemp_config.py
```

Use the interactive menu to:
- Configure servers and sensors
- Discover connected devices
- Test connectivity
- Setup auto-start on boot (cron)
- Start/stop background client
- Update from GitHub

### Manual Start
```bash
source venv/bin/activate
python3 nettemp_client.py
```

### Auto-start on boot
Configured via `nettemp_config.py` → System Management → Setup Auto-Start.
Client runs automatically on boot via cron.

### Test Mode (fake data)
```bash
python3 demo_all_sensors.py
```

## Sending Data Manually (HTTP Bridge)

If you enable the optional `http_bridge` in `config.conf`, your Nettemp client exposes a lightweight HTTP endpoint (default: http://0.0.0.0:8080). You can POST data directly over HTTP and the client forwards it securely to Nettemp Cloud using the configured API key. This is handy for device firmwares that only speak HTTP.

### Enable HTTP Bridge

```yaml
http_bridge:
  enabled: true
  host: 0.0.0.0
  port: 8080
  auth_token: local_shared_secret   # optional but recommended
```

### 1. Cloud Payload (Device + readings)

```bash
curl -X POST http://your-client:8080/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer local_shared_secret" \
  -d '{
        "device_id": "living-room-1",
        "readings": [
          {
            "sensor_id": "1b-28_000007165506",
            "sensor_type": "temperature",
            "value": 21.75,
            "unit": "°C",
            "timestamp": 1732036297,
            "metadata": {
              "name": "Living Room Temp",
              "original_rom": "28-000007165506"
            }
          }
        ]
      }'
```

Python example:

```python
import requests, time

payload = {
    "device_id": "living-room-1",
    "readings": [
        {
            "sensor_id": "1b-28_000007165506",
            "sensor_type": "temperature",
            "value": 21.75,
            "unit": "°C",
            "timestamp": int(time.time())
        }
    ]
}

resp = requests.post(
    "http://your-client:8080/",
    json=payload,
    headers={"Authorization": "Bearer local_shared_secret"}
)
resp.raise_for_status()
```

### 2. Legacy Payload (list of ROM/value objects)

```bash
curl -X POST http://your-client:8080/ \
  -H "Content-Type: application/json" \
  -d '[{"rom":"28-000007165506","type":"temperature","value":21.75,"unit":"°C","name":"Living Room"}]'
```

In Python:

```python
legacy = [
    {"rom":"28-000007165506","type":"temperature","value":21.75,"unit":"°C","name":"Living Room"}
]

requests.post("http://your-client:8080/", json=legacy)
```

The client forwards legacy payloads via `insert2` (local server + cloud), and forwards the new cloud format directly to your configured cloud servers.

### 3. ESP Easy "Generic HTTP" (GET)

Point ESP Easy’s `Generic HTTP` controller at the bridge URL:

```
http://your-client:8080/generic_http?name=%sysname%&task=%tskname%&valuename=%valname%&value=%value%
```

You can test it manually:

```bash
curl "http://your-client:8080/generic_http?name=esp1&task=dht22&valuename=temperature&value=23.4&unit=%25"
```

The bridge converts that into the legacy format and forwards it just like a local driver reading.

## Updating

### Quick Update (Recommended)

```bash
cd nettemp_client
python3 nettemp_config.py
# Select: System Management → Update from GitHub
```

The interactive update tool automatically:
- ✅ Stops the running client
- ✅ Pulls latest changes from GitHub
- ✅ Updates Python dependencies
- ✅ Preserves your configurations
- ✅ Offers to restart the client

### Manual Update

```bash
# Navigate to installation directory
cd nettemp_client

# Pull latest changes
git pull origin main

# Update Python dependencies
source venv/bin/activate
pip3 install -r requirements.txt --upgrade

# Restart the client
python3 nettemp_client.py
```

**Your configurations are safe:**
- `config.conf` - Your device settings are preserved
- `drivers_config.yaml` - Your sensor configurations are preserved

The update only modifies:
- Code files (*.py)
- Example templates (`example_config.conf`, `example_drivers_config.yaml`)
- Documentation
- Default driver files

**Note:** If new configuration options are added, check `example_config.conf` or `example_drivers_config.yaml` for reference.

## File Structure

```
client/
├── nettemp_config.py              # Interactive configuration tool (all-in-one)
├── nettemp_client.py              # Production runner (scheduled)
├── nettemp.py                     # Cloud client library
├── driver_loader.py               # Driver management
├── example_config.conf            # Config template (tracked in git)
├── example_drivers_config.yaml    # Drivers template (tracked in git)
├── config.conf                    # Your device settings (git ignored)
├── drivers_config.yaml            # Your sensor config (git ignored)
├── demo_all_sensors.py            # Test with fake data
├── drivers/                       # Sensor drivers
│   ├── system.py
│   ├── dht22.py
│   ├── bme280.py
│   └── ...
└── requirements.txt               # Python dependencies
```

## Hardware Setup

### I2C Sensors
```bash
# Enable I2C
sudo raspi-config
# Interface Options → I2C → Enable

# Check I2C devices
i2cdetect -y 1
```

### GPIO Sensors (DHT22, DHT11)
Connect to GPIO pins as configured in `drivers_config.yaml`.

### BLE Sensors (Xiaomi LYWSD03MMC)

The `lywsd03mmc` driver supports Xiaomi Mi Temperature Humidity Sensor 2 via Bluetooth Low Energy.

**Hardware Requirements:**
- Raspberry Pi with Bluetooth (Pi 3, 4, Zero W, or USB BLE dongle)
- Xiaomi LYWSD03MMC sensor (CR2032 battery powered)

**Dependencies:**
```bash
# Install BLE libraries
pip3 install adafruit-circuitpython-ble
pip3 install adafruit-circuitpython-ble-lywsd03mmc
```

**Configuration:**
```yaml
# In drivers_config.yaml:
lywsd03mmc:
  enabled: true
  read_in_sec: 300
  device_name: "LYWSD03MMC"  # BLE device name
  mac_address: null          # Optional: MAC address for specific sensor
  sensor_id: "default"       # Unique ID for multiple sensors
```

**Multiple Sensors:**
To use multiple LYWSD03MMC sensors, create separate entries with different IDs:
```yaml
lywsd03mmc_living:
  enabled: true
  read_in_sec: 300
  device_name: "LYWSD03MMC"
  mac_address: "A4:C1:38:XX:XX:XX"
  sensor_id: "living_room"

lywsd03mmc_bedroom:
  enabled: true
  read_in_sec: 300
  device_name: "LYWSD03MMC"
  mac_address: "A4:C1:38:YY:YY:YY"
  sensor_id: "bedroom"
```

**Finding MAC Address:**
```bash
# Scan for BLE devices
sudo hcitool lescan
# Look for "LYWSD03MMC" and note the MAC address
```

**Troubleshooting:**
- Ensure Bluetooth is enabled: `sudo systemctl status bluetooth`
- Check BLE scan: `sudo hcitool lescan`
- Run client with sudo for BLE access: `sudo python3 nettemp.py`
- Keep sensor within 10m range
- Replace battery if readings fail intermittently

### Modbus RTU Sensors (SDM120)

The SDM120 power meter uses Modbus RTU over RS485 serial interface.

**Hardware Setup:**
```bash
# Connect USB-to-RS485 adapter to Raspberry Pi
# Check device appears as /dev/ttyUSB0 (or /dev/ttyAMA0)
ls -la /dev/tty*

# Add user to dialout group for serial access
sudo usermod -a -G dialout $USER
sudo reboot
```

**Configuration:**
```yaml
# In drivers_config.yaml:
sdm120:
  enabled: true
  read_in_sec: 60
  port: /dev/ttyUSB0  # Serial port
  unit: 1              # Modbus unit ID (check meter display/settings)
  baudrate: 9600       # Common: 9600, 19200, 38400
  parity: "N"          # N=None, E=Even, O=Odd
```

**Dependencies:**
```bash
# Install Modbus libraries
pip install pymodbus==2.5.3 sdm-modbus==0.5.0
```

**Troubleshooting:**
- Verify serial port permissions: `sudo chmod 666 /dev/ttyUSB0`
- Check Modbus unit ID on meter (default is often 1 or 2)
- Verify baudrate matches meter settings
- Check RS485 wiring (A/B polarity, termination resistor)
- Test connection: Check logs for "No response from meter" errors

### 1-Wire (DS18B20 Temperature Sensors)

The `w1_kernel` driver supports multiple connection methods:

**Option 1: Direct GPIO Connection**
```bash
# Enable 1-wire via raspi-config
sudo raspi-config
# Interface Options → 1-Wire → Enable

# Or manually add to /boot/config.txt:
dtoverlay=w1-gpio,gpiopin=4  # Default GPIO 4

# Reboot to apply
sudo reboot

# Check for sensors
ls /sys/bus/w1/devices/
# Example: 28-000007165506
```

**Option 2: DS2482 I2C-to-1Wire Bridge (for many sensors)**
```yaml
# In drivers_config.yaml:
w1_kernel:
  enabled: true
  read_in_sec: 60
  ds2482: true  # Enables DS2482 initialization at startup
```

The DS2482 bridge (I2C address 0x18) allows connecting **many 1-Wire sensors** over a single I2C bus:
- Supports up to 8 channels (DS2482-800)
- Long cable runs (100+ meters)
- Better noise immunity than GPIO
- Hardware is initialized automatically on startup
- Compatible with Nettemp Pi HAT and generic DS2482 breakout boards

**Option 3: Dallas Semiconductor DS9490R USB 1-Wire Adapter**

The DS9490R is a USB-to-1Wire adapter that appears as a kernel 1-wire master:

```bash
# Install kernel module (usually pre-installed)
sudo modprobe ds2490

# Connect DS9490R USB adapter
# Sensors will appear in /sys/bus/w1/devices/

# Enable in config:
w1_kernel:
  enabled: true
  read_in_sec: 60
  # No ds2482 flag needed - kernel handles USB adapter automatically
```

The USB adapter is ideal for:
- Systems without GPIO (x86, laptops, servers)
- Galvanically isolated 1-Wire networks
- Hot-pluggable sensor networks
- Testing without Raspberry Pi

All three methods auto-discover connected DS18B20 sensors and create separate sensor readings for each device.

Note about the Nettemp Pi HAT / DS2482 addon
-------------------------------------------
There was a Nettemp Pi HAT (DS2482-based 1-Wire bridge) sold previously via Kamami. The product page (now withdrawn) is available for historical reference:

https://kamami.pl/wycofane-z-oferty/559377-nettemp-pi-hat-modul-nettemp-dla-komputera-raspberry-pi.html

This specific HAT appears to be discontinued from that supplier. If you need the same functionality today, you can use any compatible DS2482 I2C-to-1-Wire bridge breakout (for example modules labeled DS2482-800) or run multiple DS18B20 sensors directly on the Pi\'s 1-Wire GPIO (if wiring allows).

To enable DS2482 support in this client, set `ds2482: true` under `w1_kernel` in `drivers_config.yaml` (example above). The driver will attempt to initialize the DS2482 bridge on startup.

## Troubleshooting

**No sensors found:**
- Check hardware connections
- Verify I2C enabled: `i2cdetect -y 1`
- Check GPIO pins match config
-- Install sensor libraries: `pip install -r requirements.txt`

**Cannot connect to server:**
- Check `cloud_server` URL (cloud or self-hosted)
- Verify `cloud_api_key` is valid
- Test connection:
  - Cloud: `curl https://your-worker.workers.dev`
  - Self-hosted: `curl http://your-server:8787`

**Data not showing in dashboard:**
- Check `cloud_enabled: true`
- Verify device name (`group`) is correct
- Check logs: `python3 nettemp_client.py`

**Permission denied (I2C):**
```bash
sudo usermod $USER -aG i2c
sudo reboot
```

## Adding Custom Drivers

Create `drivers/my_sensor.py`:

```python
def my_sensor(config_dict):
    """
    My custom sensor
    Config: {"enabled": true, "read_in_sec": 60, ...}
    """
    value = read_hardware()

    return [
        {
            "rom": "_my_sensor",
            "type": "temperature",
            "value": value,
            "name": "My Sensor"
        }
    ]
```

Add to `drivers_config.yaml`:
```yaml
my_sensor:
  enabled: true
  read_in_sec: 60
```

## Uninstall

```bash
# Remove cron job
crontab -l | grep -v nettemp_client | crontab -

# Remove files
rm -rf /path/to/nettemp_cloud/client
```

## Community & Resources

**Discord Server** - Get help, share projects, and discuss development:  
https://discord.gg/S4egxNvQHM

**Main Repository** - Backend, Docker setup, and documentation:  
https://github.com/sosprz/nettemp

**Docker Hub** - Pre-built container images:  
https://hub.docker.com/r/przemeksdocker/nettemp

## Support

See main repository for backend deployment and dashboard documentation.

## API Usage Examples

The API host for client devices is `https://api.nettemp.pl`. Below are simple examples for sending sensor data.

### cURL (POST bulk data)

Use a heredoc with `-d @-` to keep the payload readable and avoid escaping:

```bash
curl -X POST "https://api.nettemp.pl/api/v1/data" \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ntk_YOUR_API_KEY' \
  -d @- <<'JSON'
{
  "device_id": "device-1",
  "readings": [
    {"sensor_id": "s1", "type": "temperature", "value": 22.4},
    {"sensor_id": "s2", "type": "humidity", "value": 55.1}
  ]
}
JSON
```

**Note:** The server enforces a maximum of 100 unique sensors per request. If you have more sensors, split them into batches of <= 100 readings per request.

### Python (requests)

```python
import requests

url = "https://api.nettemp.pl/api/v1/data"
headers = { 'Authorization': 'Bearer ntk_YOUR_API_KEY', 'Content-Type': 'application/json' }
payload = {
  "device_id": "device-1",
  "readings": [
    {"sensor_id": "s1", "type": "temperature", "value": 22.4},
    {"sensor_id": "s2", "type": "humidity", "value": 55.1}
  ]
}
resp = requests.post(url, json=payload, headers=headers)
print(resp.status_code, resp.text)
```

### JavaScript (fetch)

```javascript
const url = 'https://api.nettemp.pl/api/v1/data';
const payload = {
  device_id: 'device-1',
  readings: [
    { sensor_id: 's1', type: 'temperature', value: 22.4 },
    { sensor_id: 's2', type: 'humidity', value: 55.1 }
  ]
};

fetch(url, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ntk_YOUR_API_KEY'
  },
  body: JSON.stringify(payload)
}).then(r => r.json()).then(console.log).catch(console.error);
```

For large sensor sets, chunk readings into batches of at most 100 unique sensors per request and retry on transient failures.

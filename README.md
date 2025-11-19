# Nettemp Client

IoT sensor client for Raspberry Pi and other Linux devices. Reads sensors and sends data to **Nettemp Cloud** or **self-hosted Nettemp** instance.

**☁️ Cloud** - Managed hosting on Cloudflare Workers *(Coming Soon!)*
**🏠 Self-Hosted** - Deploy to your own server/VPS *(Available Now)*

> **Note:** Nettemp Cloud (managed service) is currently in development. You can use the self-hosted option today by deploying the backend to your own infrastructure.

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

# 2. Run setup script
chmod +x setup.sh
./setup.sh

# 3. Configure (edit these files)
nano config.conf         # Set your server URL and API key
nano drivers_config.yaml # Enable sensors you have

# 4. Test
source venv/bin/activate
python3 nettemp_client.py

# 5. Reboot to enable auto-start
sudo reboot
```

### Manual Installation

As an alternative to the setup script, you can install the dependencies manually.

```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Edit config files
nano config.conf
nano drivers_config.yaml

# Run the client
python3 nettemp_client.py
```

## Configuration

### 1. Device Settings (config.conf)

**For Self-Hosted Deployment** *(Available Now)*
```yaml
group: living-room-1              # Your device name
cloud_server: http://192.168.1.100:8787  # Your server IP/domain
cloud_api_key: ntk_xxxxx          # Get from your instance
cloud_enabled: true
```

**For Cloud Deployment** *(Coming Soon)*
```yaml
group: living-room-1              # Your device name
cloud_server: https://api.nettemp.cloud
cloud_api_key: ntk_xxxxx          # Get from dashboard
cloud_enabled: true
```

### 2. Sensor Settings (drivers_config.yaml)

```yaml
system:
  enabled: true                   # Enable CPU/RAM monitoring
  read_in_sec: 60                 # Read every 60 seconds

dht22:
  enabled: true
  read_in_sec: 60
  gpio_pin: 4                     # Connected to GPIO4

bme280:
  enabled: true
  read_in_sec: 60
  i2c_address: "0x76"            # I2C address
```

## Available Drivers

<div align="center">
<img src="img/nettemp-raspi.jpg" alt="Nettemp Raspberry Pi HAT" width="360" style="margin:8px" />
<img src="img/nettemp-sensors1.jpg" alt="Nettemp sensors" width="360" style="margin:8px" />
</div>

**System:**
- `system` - CPU, RAM usage
- `rpi` - Raspberry Pi CPU temperature
- `lm_sensors` - Linux hardware sensors

**Temperature:**
- `w1_kernel` - DS18B20 (1-Wire, supports DS2482 I2C bridge)
- `w1_kernel_gpio` - DS18B20 via GPIO
- `dht11`, `dht22` - DHT sensors (GPIO)
- `bme280`, `bmp180` - I2C sensors
- `tmp102`, `htu21d`, `hih6130`, `mpl3115a2`

**Light:**
- `bh1750`, `tsl2561`

**Motion:**
- `adxl343`, `adxl345` - Accelerometers

**Distance:**
- `vl53l0x`

**Network:**
- `ping` - Network latency

**Modbus:**
- `sdm120` - Power meter

## Running

### Manual Start
```bash
source venv/bin/activate
python3 nettemp_client.py
```

### Auto-start (configured by setup.sh)
Runs automatically on boot via cron.

### Test Mode (fake data)
```bash
python3 demo_all_sensors.py
```

## Updating

### Quick Update (Recommended)

```bash
cd nettemp_client
./update.sh
```

The update script automatically:
- Stops the running client
- Pulls latest changes from GitHub
- Updates Python dependencies
- Restarts the client
- Preserves your configurations

### Manual Update

```bash
# Navigate to installation directory
cd nettemp_client

# Stop the running client (if running interactively)
# Press Ctrl+C to stop

# Pull latest changes
git pull origin main

# Update Python dependencies
source venv/bin/activate
pip3 install -r requirements.txt --upgrade

# Restart the client
python3 nettemp_client.py

# Or reboot to restart via cron
sudo reboot
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
├── setup.sh                       # Installation script
├── update.sh                      # Update script
├── example_config.conf            # Config template (tracked in git)
├── example_drivers_config.yaml    # Drivers template (tracked in git)
├── config.conf                    # Your device settings (git ignored)
├── drivers_config.yaml            # Your sensor config (git ignored)
├── nettemp_client.py             # Production runner (scheduled)
├── nettemp.py                    # Cloud client library
├── driver_loader.py              # Driver management
├── demo_all_sensors.py           # Test with fake data
├── drivers/                       # Sensor drivers
│   ├── system.py
│   ├── dht22.py
│   ├── bme280.py
│   └── ...
└── requirements.txt              # Python dependencies
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

### 1-Wire (DS18B20)

**Option 1: Direct GPIO connection**
```bash
# Enable 1-wire
sudo raspi-config
# Interface Options → 1-Wire → Enable

# Or add to /boot/config.txt:
dtoverlay=w1-gpio
```

**Option 2: DS2482 I2C Bridge (for multiple sensors)**
```yaml
# In drivers_config.yaml:
w1_kernel:
  enabled: true
  read_in_sec: 60
  ds2482: true  # Enables DS2482 initialization at startup
```
The DS2482 bridge allows connecting many 1-Wire sensors over I2C. Hardware is initialized automatically on startup.

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

## Deployment Options

### ☁️ Nettemp Cloud *(Coming Soon)*
- ✅ Fully managed service
- ✅ No server setup required
- 🚧 Currently in development


### 🏠 Self-Hosted *(Available Now)*
- ✅ Full control over your data
- ✅ Run on your own infrastructure
- ✅ No external dependencies
- ✅ LAN-only option (offline mode)
- ✅ Deploy to any server/VPS

Docker image
------------
A Docker image is available for easier self-hosted deployment: przemeksdocker/nettemp. You can run the client or the server in a container if you prefer containerized deployments. Check the Docker Hub or the `przemeksdocker/nettemp` repository for usage examples and tags.

Docker Hub
----------
Pull or inspect the published image on Docker Hub:

https://hub.docker.com/r/przemeksdocker/nettemp

Community
---------
Join the project Discord server for help, discussions, and announcements:

https://discord.gg/S4egxNvQHM

Nettemp Docker repository
------------------------
The main Nettemp project includes Docker deployment examples and images — see the repository for server and containerized setups:

https://github.com/sosprz/nettemp

Use that repository for Docker Compose examples and instructions to run Nettemp (server) and the client in containers.

**Quick start:** Clone the backend repository and follow deployment instructions.

Both options use the same client - just change the `cloud_server` URL in config.

## Support

See main repository for backend deployment and dashboard documentation.

## API Usage Examples

The API host for client devices is `https://api.client.nettemp.pl`. Below are simple examples for sending sensor data.

### cURL (POST bulk data)

Use a heredoc with `-d @-` to keep the payload readable and avoid escaping:

```bash
curl -X POST "https://api.client.nettemp.pl/api/v1/data" \
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

url = "https://api.client.nettemp.pl/api/v1/data"
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
const url = 'https://api.client.nettemp.pl/api/v1/data';
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
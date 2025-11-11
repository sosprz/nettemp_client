#!/bin/bash

echo "========================================="
echo "  Nettemp Client Setup"
echo "  (Cloud & Self-Hosted)"
echo "========================================="
echo ""

# Update system
echo "[1/6] Updating system packages..."
sudo apt-get update
sudo apt-get -y install python3-pip python3-venv lm-sensors

# Create virtual environment
echo "[2/6] Creating Python virtual environment..."
python3 -m venv venv

# Activate and install dependencies
echo "[3/6] Installing Python dependencies..."
. venv/bin/activate
pip3 install -r requirements.txt

# Initialize config
echo "[4/6] Initializing configuration..."
python3 -c "from driver_loader import DriverLoader; print('Config check OK')" || echo "Warning: Config check failed"

deactivate

# Setup cron for auto-start
echo "[5/6] Setting up auto-start (cron)..."
cron_data=$(crontab -l 2>/dev/null)
grep -q "nettemp_client" <<< "$cron_data"

if [ $? -eq 1 ] ; then
    echo "@reboot /bin/sleep 30 && $(pwd)/venv/bin/python3 $(pwd)/nettemp_client.py &" > nettemp_crontab
    crontab nettemp_crontab
    echo "✓ Cron job added"
else
    echo "✓ Cron job already exists"
fi

echo ""
echo "### Current crontab:"
crontab -l
echo ""

# Add user to i2c group
echo "[6/6] Adding user to I2C group..."
sudo usermod $USER -aG i2c

echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit config.conf:"
echo "   - Set your device name (group)"
echo "   - Add server URL (cloud_server) - use your self-hosted instance"
echo "   - Add your API token (cloud_api_key)"
echo "   Note: Nettemp Cloud (managed service) coming soon!"
echo ""
echo "2. Edit drivers_config.yaml:"
echo "   - Enable sensors you have"
echo "   - Set reading intervals"
echo "   - Configure sensor parameters (GPIO pins, I2C addresses, etc.)"
echo ""
echo "3. Test the setup:"
echo "   source venv/bin/activate"
echo "   python3 driver_loader.py        # Check config"
echo "   python3 nettemp_client.py       # Run manually"
echo ""
echo "4. Or test with fake data:"
echo "   python3 demo_all_sensors.py     # Send fake sensor data"
echo ""
echo "5. Reboot to start automatically:"
echo "   sudo reboot"
echo ""
echo "========================================="

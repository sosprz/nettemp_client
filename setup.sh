#!/bin/bash

sudo apt-get update
sudo apt-get -y install python3-pip python3-venv lm-sensors

python3 -m venv venv
. venv/bin/activate
pip3 install -r requirements.txt
python3 config.py

deactivate

cron_data=$(crontab -l)
grep  -q "nettemp_client" <<< $cron_data

if [ $? -eq 1 ] ; then
    echo "@reboot /bin/nohup $(pwd)/venv/bin/python3 $(pwd)/nettemp_client.py &" > nettemp_crontab
    crontab nettemp_crontab
fi

echo "### crontab -l"
crontab -l
echo "### end crontab"

echo "### Add $USER to I2C group"
sudo usermod $USER -aG i2c

echo "### 1. edit config.conf to add server IP and api key token"
echo "### 2. edit drivers.conf to enable drivers for sensors"








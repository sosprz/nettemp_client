#!/bin/bash

sudo apt-get update
sudo apt-get -y install python3-pip python3-venv

python3 -m venv venv
. venv/bin/activate
pip3 install w1thermsensor requests apscheduler pyaml psutil smbus gpiozero
pip3 install git+https://github.com/nicmcd/vcgencmd.git
pip3 install adafruit-circuitpython-htu21d adafruit-circuitpython-tsl2561 Adafruit-BMP adafruit-circuitpython-adxl34x \
 adafruit-circuitpython-dht adafruit-circuitpython-vl53l0x

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

echo "Add $USER to I2C group"
sudo usermod $USER -aG i2c







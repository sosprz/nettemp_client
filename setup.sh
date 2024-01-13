#!/bin/bash

sudo apt-get update
sudo apt-get -y install python3-pip python3-venv

python3 -m venv venv
. venv/bin/activate
pip3 install w1thermsensor requests apscheduler pyaml psutil smbus gpiozero
pip3 install git+https://github.com/nicmcd/vcgencmd.git
pip3 install adafruit-circuitpython-htu21d adafruit-circuitpython-tsl2561 Adafruit-BMP adafruit-circuitpython-adxl34x adafruit-circuitpython-dht

deactivate

cron=$(crontab -l|grep nettemp_client)
if  [ ! -z "$cron" ]
    echo "@reboot /bin/nohup $(pwd)/venv/bin/python3 $(pwd)/nettemp_client.py &" > nettemp_crontab
    crontab nettemp_crontab

echo "Add $USER to I2C group"
sudo usermod $USER -aG i2c






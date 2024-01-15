git pull
python3 -m venv venv
. venv/bin/activate
pip3 install w1thermsensor requests apscheduler pyaml psutil smbus gpiozero
pip3 install git+https://github.com/nicmcd/vcgencmd.git
pip3 install adafruit-circuitpython-htu21d adafruit-circuitpython-tsl2561 Adafruit-BMP adafruit-circuitpython-adxl34x \
 adafruit-circuitpython-dht adafruit-circuitpython-vl53l0x
pip3 install pingparsing
python3 config.py
pkill -f nettemp_client.py
/bin/nohup $(pwd)/venv/bin/python3 $(pwd)/nettemp_client.py &

git pull
python3 config.py
pkill -f nettemp_client.py
/bin/nohup $(pwd)/venv/bin/python3 $(pwd)/nettemp_client.py &

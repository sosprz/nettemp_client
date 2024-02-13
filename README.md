
##### General info

Nettemp client uses python3 and virtual enviroment.
Remember turn on I2C and 1wire on raspberry pi devices over raspi-config. 
Drivers like ds2482 require root perms. On raspberry pi no action required or system where user has sudo.

##### Download and setup nettemp_client

```
git clone https://github.com/sosprz/nettemp_client
cd nettemp_client
bash ./setup.sh
```

##### Set server IP and API key in config file.  


```
nano config.conf
```

```
server_ip: 172.18.10.105
server_api_key: o39-SumAuuAMyY1lUuVlllj2h08HXr-F4heUKzIpeyo
```

##### Enable sensors 

```
nano drivers.conf
```
```
w1_kernel:
    enabled: true
    read_in_sec: 60
system:
    enabled: true
    read_in_sec: 60

...
...

```

##### Run app:

```
/home/pi/nettemp_client/venv/bin/python3 /home/pi/nettemp_client/nettemp_client.py
```

##### Add to cron:

Script setup.sh will do this for You.

##### Check if job is already in cron:

```
crontab -l
@reboot /bin/nohup /home/pi/nettemp_client/venv/bin/python3 /home/pi/nettemp_client/nettemp_client.py

```








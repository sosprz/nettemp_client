import paho.mqtt.publish as publish
import yaml, json
import logging

def send_to_mqtt_broker(group, topic, data):
    
    topic = f"nettemp/{group}/{topic}"
    message = data
    
    config_file = open("config.conf")
    config = yaml.load(config_file, Loader=yaml.FullLoader)
    broker = config["mqtt_server"]
    port = config["mqtt_port"]
    username = config["mqtt_username"]
    password = config["mqtt_password"]
    
    if config and port and broker and message and broker != 'empty':
      
        auth = {
            'username': username,
            'password': password
        }

        message = json.dumps(data)

        # Publish the message
        try:
            if auth['username']:
                publish.single(topic, payload=message, hostname=broker, port=port, auth=auth)
            else:
                publish.single(topic, payload=message, hostname=broker, port=port)
            logging.info(f" Data published to {topic}")
        except Exception as e:
            logging.info(f" Failed to publish message to {topic}. Error: {e}")
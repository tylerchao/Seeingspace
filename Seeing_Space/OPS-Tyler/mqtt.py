import json
import random
import time
import datetime

from paho.mqtt import client as mqtt_client

broker = 'localhost'
port = 1883
#topic = "python/mqtt"

class mqtt():
    def connect_mqtt():
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("Connected to MQTT Broker!")
            else:
                print("Failed to connect, return code %d\n", rc)

        client = mqtt_client.Client()
        client.on_connect = on_connect
        client.connect(broker, port)
        return client

    def publish(client,topic,msg):
        time = datetime.datetime.now()
        timepstamp = time.strftime("%Y%m%d_%H%M%S")

        send_msg = {"time" : timepstamp, "value": msg}

        payload = json.dumps(send_msg)

        result = client.publish(topic, payload)

        # result: [0, 1]
        status = result[0]
        if status == 0:
            print(f"Send `{payload}` to topic `{topic}`")
        else:
            print(f"Failed to send message to topic {topic}")

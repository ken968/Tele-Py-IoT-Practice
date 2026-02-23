import paho.mqtt.client as mqtt
import json
import time
import random

BROKER = "localhost"
# PORT = 1883
TOPIC = "sensor/dht22"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(BROKER, 1883)

print('virtual sensor aktip')

try:
    while True:
        payload = {
            "device_id": "python_virtual_01",
            "suhu": round(random.uniform(16, 35), 1),
            "kelembapan": round(random.uniform(40, 60), 1)
        }


        client.publish(TOPIC, json.dumps(payload))
        print(f"Published: {payload}")
        time.sleep(11)

except KeyboardInterrupt:
    print("program dihentikan")
    client.disconnect()


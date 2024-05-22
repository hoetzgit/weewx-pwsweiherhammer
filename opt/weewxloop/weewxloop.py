import paho.mqtt.client as mqtt
import json
from json import JSONDecodeError
import time
import os
import sys
import systemd.daemon
import fcntl

MQTT_BROKER = "mqtt.fritz.box"
MQTT_TOPIC = "weewx-mqtt/loop"
MQTT_USER = "weewx"
MQTT_PASSWORD = "weewx"
MQTT_CLIENT_ID = "weewxloop"
JSON_FILE_PATH = "/home/weewx/public_html/data/json/current_weewx.json"
MAX_JSON_AGE = 600  # Max age of JSON file in seconds (10 minutes)

def exit_with_error(message):
    print(message)
    sys.exit(1)

def on_disconnect(client, userdata, rc=0):
    print("DisConnected result code %s" % str(rc))
    client.loop_stop()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker %s" % MQTT_BROKER)
        client.subscribe(MQTT_TOPIC)
        print("Subscribe Topic %s" % MQTT_TOPIC)
    else:
        print("Connection to MQTT broker %s failed with status %s" % (MQTT_BROKER, str(rc)))

def on_message(client, userdata, message):
    try:
        print(f"Message received from [{message.topic}]: {message.payload}")
        if message.payload is None:
            print("Error message is a None string.")
            return
        data = str(message.payload.decode('utf-8', 'ignore'))
        if validate_json(data):
            data = json.loads(data)
            write_json_to_file(data)
        else:
            print("Error message is not a valid json string")
    except ValueError as e:
        #exit_with_error("Error processing MQTT message: %s" % str(e))
        print("Error processing MQTT message: %s" % str(e))
    except Exception as e:
        #exit_with_error("Error processing MQTT message: %s" % str(e))
        print("Error processing MQTT message: %s" % str(e))

def write_json_to_file(data):
    try:
        with open(JSON_FILE_PATH, "w") as json_file:
            fcntl.flock(json_file, fcntl.LOCK_EX)  # Acquire an exclusive lock
            json.dump(data, json_file, indent=4)   # Indent for better readability
            fcntl.flock(json_file, fcntl.LOCK_UN)  # Release the lock
        print("JSON data written to file.")
        return True
    except Exception as e:
        exit_with_error("Error processing MQTT message: %s" % str(e))

def validate_json(data):
    try:
        json.loads(str(data))
        return True
    except JSONDecodeError:
        return False

def check_json_age():
    if os.path.exists(JSON_FILE_PATH):
        file_age = time.time() - os.path.getmtime(JSON_FILE_PATH)
        if file_age > MAX_JSON_AGE:
            os.remove(JSON_FILE_PATH)
            print("Removed outdated JSON file")

# def main():
    # client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    # client.username_pw_set(username=MQTT_USER, password=MQTT_PASSWORD)
    # client.on_connect = on_connect
    # client.on_disconnect = on_disconnect
    # client.on_message = on_message

    # while not client.is_connected():
        # try:
            # print("Connecting to MQTT broker...")
            # client.connect(MQTT_BROKER)
            # client.loop_start()
            # time.sleep(4)
        # except:
            # print("Connection failed. Retrying in 1 minute...")
            # time.sleep(60)

    # while True:
        # try:
            # check_json_age()
            # client.loop()
            # systemd.daemon.notify("WATCHDOG=1")
        # except Exception as e:
            # client.disconnect()
            # exit_with_error("Error processing MQTT message: %s" % str(e))
        # time.sleep(60)

def main():
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.username_pw_set(username=MQTT_USER, password=MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print("Connecting to MQTT broker...")
        client.connect(MQTT_BROKER)
    except:
        print("Connection failed.")
        return

    client.loop_forever()  # Der Client wird in einer Endlosschleife ausgeführt

if __name__ == "__main__":
    main()

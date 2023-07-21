from flask import Flask, request, jsonify, make_response,json
import paho.mqtt.client as mqtt
import requests


app = Flask(__name__)

# MQTT
mqtt_host = "gopher.phynetlab.com"
mqtt_port = 8883
mqtt_topic = "/fms/order"
mqtt_client_id = "GatewayServer"
mqtt_messages = []


def on_connect(client, userdata, flags, rc):
    client.subscribe(mqtt_topic)
    print("Connected to MQTT broker with result code: " + str(rc))


def on_message(client, userdata, msg):
    message = msg.payload.decode("utf-8")
    print("Received message:", message)

    try:
        response = requests.get("http://localhost:8760/mqtt", params={"message": message})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Failed to send HTTP request:", str(e))


def connect_to_mqtt_broker():
    mqtt_client = mqtt.Client(client_id=mqtt_client_id)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(mqtt_host, mqtt_port, keepalive=60)
    mqtt_client.loop_start()


@app.route('/mqtt', methods=['GET'])
def handle_mqtt_request():
    global mqtt_message
    message = request.args.get('message')

    if message:
        mqtt_message = message

    if mqtt_message:
        return make_response(jsonify(mqtt_message))
    else:
        return make_response(jsonify("No message received"))

if __name__ == "__main__":
    connect_to_mqtt_broker()
    app.run(host="0.0.0.0", port=8760)

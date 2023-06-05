package com.phynode1.Phynode1;

import org.eclipse.paho.client.mqttv3.*;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@SpringBootApplication
public class Phynode1Application {

	public static void main(String[] args) {
		SpringApplication.run(Phynode1Application.class, args);

		String mqttHost = "gopher.phynetlab.com";
		int mqttPort = 8883;
		String mqttTopic = "/fms/order";
		String clientId = "GatewayServer";

		try {
			MqttClient mqttClient = new MqttClient("tcp://" + mqttHost + ":" + mqttPort, clientId, new MemoryPersistence());
			MqttConnectOptions connectOptions = new MqttConnectOptions();
			mqttClient.connect(connectOptions);

			mqttClient.setCallback(new MqttCallback() {
				@Override
				public void connectionLost(Throwable cause) {
					System.out.println("Connection lost: " + cause.getMessage());
				}

				@Override
				public void messageArrived(String topic, MqttMessage message) throws Exception {
					System.out.println("Received message:");
					System.out.println("Topic: " + topic);
					System.out.println("Message: " + new String(message.getPayload()));
					System.out.println("========================================");
				}

				@Override
				public void deliveryComplete(IMqttDeliveryToken token) {
					// Not used in this example
				}
			});

			mqttClient.subscribe(mqttTopic);
			System.out.println("Subscribed to topic: " + mqttTopic);

		} catch (MqttException e) {
			System.out.println("MQTT subscription failed: " + e.getMessage());
		}
	}
}

@RestController
@RequestMapping("/mqtt")
class MQTTController {

	private final String mqttMessage;

	public MQTTController() {
		this.mqttMessage = null;
	}

	@GetMapping
	public ResponseEntity<String> getMQTTMessage() {
		if (mqttMessage != null) {
			System.out.println(mqttMessage);
			return ResponseEntity.ok(mqttMessage);
		} else {
			System.out.println("No message");
			return ResponseEntity.ok("No message");
		}
	}

	@PostMapping
	public ResponseEntity<String> publishMQTTMessage(@RequestBody String jsonMessage) {
		try {
			String mqttHost = "gopher.phynetlab.com";
			int mqttPort = 8883;
			String mqttTopic = "/fms/order";
			String clientId = "GatewayServer";

			MqttClient mqttClient = new MqttClient("tcp://" + mqttHost + ":" + mqttPort, clientId, new MemoryPersistence());
			MqttConnectOptions connectOptions = new MqttConnectOptions();
			mqttClient.connect(connectOptions);

			MqttMessage mqttMessage = new MqttMessage(jsonMessage.getBytes());
			mqttClient.publish(mqttTopic, mqttMessage);

			return ResponseEntity.ok("Message published successfully: " + mqttMessage);

		} catch (MqttException e) {
			System.out.println("MQTT publishing failed: " + e.getMessage());
			return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
		}
	}
}

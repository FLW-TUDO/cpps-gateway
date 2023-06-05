package com.phynode1.Phynode1;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
@SpringBootApplication
@RestController
public class Phynode1Application {

	public static void main(String[] args) {
		SpringApplication.run(Phynode1Application.class, args);
	}

	@GetMapping("/")
	public String getRequest() {
		String url = "http://192.168.2.13:8760/";
		RestTemplate restTemplate = new RestTemplate();
		HttpHeaders headers = createHeaders();
		HttpEntity<String> entity = new HttpEntity<>("body", headers);
		String response = restTemplate.exchange(url, HttpMethod.GET, entity, String.class).getBody();
		System.out.println(response);
		return response;
	}

	@PostMapping("/gateway/phynodes")
	public ResponseEntity<String> handlePostRequest(@RequestBody RequestData requestData) {
		HttpHeaders headers = createHeaders();
		headers.setContentType(MediaType.APPLICATION_JSON);

		String requestPayload = String.format("{\"jobId\": \"%s\", \"request_type\": %d, \"request_payload\": {\"addr\": %d, \"module\": %d}}",
				requestData.getJobId(), requestData.getRequestType(), requestData.getAddr(), requestData.getModule());
		HttpEntity<String> entity = new HttpEntity<>(requestPayload, headers);

		RestTemplate restTemplate = new RestTemplate();
		ResponseEntity<String> responseEntity;

		try {
			responseEntity = restTemplate.postForEntity("http://192.168.2.13:8760/gateway/phynodes", entity, String.class);
			HttpStatus statusCode = (HttpStatus) responseEntity.getStatusCode();
			String responseBody = responseEntity.getBody();
			HttpHeaders responseHeaders = responseEntity.getHeaders();

			System.out.println("Response status code: " + statusCode);
			System.out.println("Response body: " + responseBody);
			System.out.println("Response headers:");
			responseHeaders.forEach((key, value) -> System.out.println(key + ": " + value));

			if (statusCode == HttpStatus.OK) {
				System.out.println("Post request successful");
			} else {
				System.out.println("Post request failed with status code: " + statusCode);
			}

			// Return response body to the browser
			return ResponseEntity.ok(responseBody);
		} catch (RestClientException e) {
			System.out.println("RestClientException: " + e.getMessage());
			return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
		}
	}


	private HttpHeaders createHeaders() {
		String auth = "AP3" + ":" + "#phynetlab#";
		byte[] encodedAuth = Base64.getEncoder().encode(auth.getBytes(StandardCharsets.US_ASCII));
		String authHeader = "Basic " + new String(encodedAuth);
		HttpHeaders headers = new HttpHeaders();
		headers.set("Authorization", authHeader);
		return headers;
	}
}

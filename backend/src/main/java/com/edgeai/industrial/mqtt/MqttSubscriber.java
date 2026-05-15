package com.edgeai.industrial.mqtt;

import com.edgeai.industrial.dto.DeviceStatusDto;
import com.edgeai.industrial.dto.SensorPayloadDto;
import com.edgeai.industrial.domain.Device;
import com.edgeai.industrial.kafka.SensorProducer;
import com.edgeai.industrial.service.DeviceService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.integration.mqtt.support.MqttHeaders;
import org.springframework.messaging.Message;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class MqttSubscriber {

    private final ObjectMapper objectMapper;
    private final DeviceService deviceService;
    private final SensorProducer sensorProducer;

    @ServiceActivator(inputChannel = "mqttInputChannel")
    public void handleMessage(Message<?> message) {
        String topic = (String) message.getHeaders().get(MqttHeaders.RECEIVED_TOPIC);
        String payload = (String) message.getPayload();

        try {
            if (topic != null && topic.startsWith("sensor/data/")) {
                handleSensorData(payload);
            } else if (topic != null && topic.startsWith("device/status/")) {
                handleDeviceStatus(payload);
            }
        } catch (Exception e) {
            log.error("Error processing MQTT message on topic {}: {}", topic, e.getMessage());
        }
    }

    private void handleSensorData(String payload) throws Exception {
        SensorPayloadDto dto = objectMapper.readValue(payload, SensorPayloadDto.class);
        log.info("MQTT received from device {} — forwarding to Kafka", dto.getDeviceId());
        sensorProducer.send(dto);
    }

    private void handleDeviceStatus(String payload) throws Exception {
        DeviceStatusDto dto = objectMapper.readValue(payload, DeviceStatusDto.class);
        Device device = deviceService.findOrCreate(dto.getDeviceId(), dto.getFirmwareVersion());
        if ("offline".equals(dto.getStatus())) {
            deviceService.markOffline(dto.getDeviceId());
        } else {
            deviceService.markOnline(device);
        }
        log.info("Device {} status: {}", dto.getDeviceId(), dto.getStatus());
    }
}

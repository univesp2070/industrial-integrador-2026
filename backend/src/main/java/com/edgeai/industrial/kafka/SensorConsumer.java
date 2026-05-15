package com.edgeai.industrial.kafka;

import com.edgeai.industrial.domain.Device;
import com.edgeai.industrial.dto.SensorPayloadDto;
import com.edgeai.industrial.service.DeviceService;
import com.edgeai.industrial.service.SensorService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class SensorConsumer {

    private final DeviceService deviceService;
    private final SensorService sensorService;

    @KafkaListener(
            topics = KafkaConfig.SENSOR_READINGS_TOPIC,
            groupId = "edge-ai-group",
            containerFactory = "kafkaListenerContainerFactory"
    )
    public void consume(SensorPayloadDto payload) {
        try {
            String firmwareVersion = payload.getInference() != null
                    ? payload.getInference().getModelVersion() : "unknown";
            Device device = deviceService.findOrCreate(payload.getDeviceId(), firmwareVersion);
            deviceService.markOnline(device);
            sensorService.saveSensorPayload(device, payload);
            log.info("Kafka consumed: device={} classification={}",
                    payload.getDeviceId(), payload.getInference().getClassification());
        } catch (Exception e) {
            log.error("Error consuming Kafka message: {}", e.getMessage());
        }
    }
}

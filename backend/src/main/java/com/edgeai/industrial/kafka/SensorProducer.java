package com.edgeai.industrial.kafka;

import com.edgeai.industrial.dto.SensorPayloadDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class SensorProducer {

    private final KafkaTemplate<String, SensorPayloadDto> kafkaTemplate;

    public void send(SensorPayloadDto payload) {
        kafkaTemplate.send(KafkaConfig.SENSOR_READINGS_TOPIC, payload.getDeviceId(), payload)
                .whenComplete((result, ex) -> {
                    if (ex != null) {
                        log.error("Failed to send to Kafka: {}", ex.getMessage());
                    } else {
                        log.debug("Kafka sent: device={} offset={}",
                                payload.getDeviceId(),
                                result.getRecordMetadata().offset());
                    }
                });
    }
}

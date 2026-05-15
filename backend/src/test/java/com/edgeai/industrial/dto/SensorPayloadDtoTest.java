package com.edgeai.industrial.dto;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class SensorPayloadDtoTest {

    private final ObjectMapper mapper = new ObjectMapper()
            .registerModule(new JavaTimeModule());

    @Test
    void deserializesMqttSensorPayload() throws Exception {
        String json = """
                {
                  "device_id": "esp32-sim-001",
                  "timestamp": "2026-05-03T12:00:00Z",
                  "sensors": {
                    "temperature": {"value": 45.2, "unit": "C"},
                    "vibration": {"value": 1.8, "unit": "mm_s"},
                    "current": {"value": 3.1, "unit": "A"}
                  },
                  "inference": {
                    "classification": "normal",
                    "anomaly_score": 0.12,
                    "model_version": "sim-v1"
                  }
                }
                """;

        SensorPayloadDto dto = mapper.readValue(json, SensorPayloadDto.class);

        assertThat(dto.getDeviceId()).isEqualTo("esp32-sim-001");
        assertThat(dto.getSensors().getTemperature().getValue()).isEqualTo(45.2);
        assertThat(dto.getInference().getClassification()).isEqualTo("normal");
        assertThat(dto.getInference().getAnomalyScore()).isEqualTo(0.12);
    }

    @Test
    void deserializesWeightSensor() throws Exception {
        String json = """
                {
                  "device_id": "wokwi-shelf-001",
                  "timestamp": "2026-05-09T10:00:00Z",
                  "sensors": {
                    "temperature": {"value": 25.0, "unit": "C"},
                    "vibration":   {"value": 0.1,  "unit": "mm_s"},
                    "current":     {"value": 2.0,  "unit": "A"},
                    "weight":      {"value": 4.75, "unit": "kg"}
                  },
                  "inference": {
                    "classification": "normal",
                    "anomaly_score": 0.05,
                    "model_version": "wokwi-v1"
                  }
                }
                """;

        SensorPayloadDto dto = mapper.readValue(json, SensorPayloadDto.class);

        assertThat(dto.getSensors().getWeight()).isNotNull();
        assertThat(dto.getSensors().getWeight().getValue()).isEqualTo(4.75);
        assertThat(dto.getSensors().getWeight().getUnit()).isEqualTo("kg");
        assertThat(dto.getPickEvent()).isNull();
    }

    @Test
    void deserializesPickEvent() throws Exception {
        String json = """
                {
                  "device_id": "wokwi-shelf-001",
                  "timestamp": "2026-05-09T10:01:00Z",
                  "sensors": {
                    "temperature": {"value": 25.0, "unit": "C"},
                    "vibration":   {"value": 0.1,  "unit": "mm_s"},
                    "current":     {"value": 2.0,  "unit": "A"},
                    "weight":      {"value": 4.675,"unit": "kg"}
                  },
                  "inference": {
                    "classification": "normal",
                    "anomaly_score": 0.05,
                    "model_version": "wokwi-v1"
                  },
                  "pick_event": {
                    "detected": true,
                    "product_name": "Parafuso M8",
                    "quantity": 3,
                    "weight_delta_kg": 0.075,
                    "confidence": 0.92
                  }
                }
                """;

        SensorPayloadDto dto = mapper.readValue(json, SensorPayloadDto.class);

        assertThat(dto.getPickEvent()).isNotNull();
        assertThat(dto.getPickEvent().isDetected()).isTrue();
        assertThat(dto.getPickEvent().getProductName()).isEqualTo("Parafuso M8");
        assertThat(dto.getPickEvent().getQuantity()).isEqualTo(3);
        assertThat(dto.getPickEvent().getWeightDeltaKg()).isEqualTo(0.075);
        assertThat(dto.getPickEvent().getConfidence()).isEqualTo(0.92);
    }
}

package com.edgeai.industrial.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import java.time.Instant;

@Data
public class SensorPayloadDto {

    @JsonProperty("device_id")
    private String deviceId;

    private Instant timestamp;

    private Sensors sensors;

    private Inference inference;

    @JsonProperty("pick_event")
    private PickEvent pickEvent;

    @Data
    public static class Sensors {
        private SensorValue temperature;
        private SensorValue vibration;
        private SensorValue current;
        private SensorValue weight;
    }

    @Data
    public static class SensorValue {
        private double value;
        private String unit;
    }

    @Data
    public static class Inference {
        private String classification;

        @JsonProperty("anomaly_score")
        private double anomalyScore;

        @JsonProperty("model_version")
        private String modelVersion;
    }

    @Data
    public static class PickEvent {
        private boolean detected;

        @JsonProperty("product_name")
        private String productName;

        private int quantity;

        @JsonProperty("weight_delta_kg")
        private double weightDeltaKg;

        private double confidence;
    }
}

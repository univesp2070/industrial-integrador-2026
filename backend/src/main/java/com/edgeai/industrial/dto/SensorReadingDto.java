package com.edgeai.industrial.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import java.time.OffsetDateTime;
import java.util.UUID;

@Data
@AllArgsConstructor
public class SensorReadingDto {
    private OffsetDateTime time;
    private UUID deviceId;
    private String deviceName;
    private String sensorType;
    private double value;
    private String unit;
    private String classification;
    private double anomalyScore;
}

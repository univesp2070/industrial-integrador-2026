package com.edgeai.industrial.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import java.time.OffsetDateTime;
import java.util.UUID;

@Data
@AllArgsConstructor
public class PickEventDto {
    private OffsetDateTime time;
    private UUID deviceId;
    private String deviceName;
    private String productName;
    private int quantity;
    private double weightDeltaKg;
    private double confidence;
}

package com.edgeai.industrial.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import java.time.Instant;

@Data
public class DeviceStatusDto {

    @JsonProperty("device_id")
    private String deviceId;

    private String status;

    @JsonProperty("firmware_version")
    private String firmwareVersion;

    @JsonProperty("uptime_seconds")
    private long uptimeSeconds;

    private Instant timestamp;
}

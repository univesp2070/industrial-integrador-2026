package com.edgeai.industrial.controller;

import com.edgeai.industrial.dto.SensorReadingDto;
import com.edgeai.industrial.service.SensorService;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/sensors")
@CrossOrigin(origins = "*")
@RequiredArgsConstructor
public class SensorController {

    private final SensorService sensorService;

    @GetMapping("/readings")
    public ResponseEntity<List<SensorReadingDto>> getReadings(
            @RequestParam UUID deviceId,
            @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime from,
            @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime to) {

        OffsetDateTime effectiveFrom = from != null ? from : OffsetDateTime.now().minusHours(1);
        OffsetDateTime effectiveTo = to != null ? to : OffsetDateTime.now();
        return ResponseEntity.ok(sensorService.getReadings(deviceId, effectiveFrom, effectiveTo));
    }

    @GetMapping("/latest")
    public ResponseEntity<List<SensorReadingDto>> getLatest() {
        return ResponseEntity.ok(sensorService.getLatestPerDevice());
    }

    @GetMapping("/recent")
    public ResponseEntity<List<SensorReadingDto>> getRecent(
            @RequestParam(defaultValue = "60") int minutes) {
        return ResponseEntity.ok(sensorService.getRecentReadings(minutes));
    }

    @GetMapping("/anomalies")
    public ResponseEntity<List<SensorReadingDto>> getAnomalies() {
        return ResponseEntity.ok(sensorService.getAnomalies());
    }
}

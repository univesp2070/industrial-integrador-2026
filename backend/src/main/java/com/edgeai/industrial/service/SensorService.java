package com.edgeai.industrial.service;

import com.edgeai.industrial.domain.Device;
import com.edgeai.industrial.dto.SensorPayloadDto;
import com.edgeai.industrial.dto.SensorReadingDto;
import com.edgeai.industrial.repository.SensorDataRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class SensorService {

    private final SensorDataRepository sensorDataRepository;
    private final PickService pickService;

    public void saveSensorPayload(Device device, SensorPayloadDto payload) {
        OffsetDateTime time = payload.getTimestamp().atOffset(ZoneOffset.UTC);
        String classification = payload.getInference().getClassification();
        double anomalyScore = payload.getInference().getAnomalyScore();

        SensorPayloadDto.Sensors s = payload.getSensors();

        sensorDataRepository.insert(time, device.getId(), device.getName(),
                "temperature", s.getTemperature().getValue(), s.getTemperature().getUnit(),
                classification, anomalyScore);

        sensorDataRepository.insert(time, device.getId(), device.getName(),
                "vibration", s.getVibration().getValue(), s.getVibration().getUnit(),
                classification, anomalyScore);

        sensorDataRepository.insert(time, device.getId(), device.getName(),
                "current", s.getCurrent().getValue(), s.getCurrent().getUnit(),
                classification, anomalyScore);

        if (s.getWeight() != null) {
            sensorDataRepository.insert(time, device.getId(), device.getName(),
                    "weight", s.getWeight().getValue(), s.getWeight().getUnit(),
                    classification, anomalyScore);
        }

        if (payload.getPickEvent() != null && payload.getPickEvent().isDetected()) {
            pickService.savePickEvent(device.getId(), time, payload.getPickEvent());
        }
    }

    public List<SensorReadingDto> getReadings(UUID deviceId, OffsetDateTime from, OffsetDateTime to) {
        return sensorDataRepository.findByDeviceAndTimeRange(deviceId, from, to);
    }

    public List<SensorReadingDto> getLatestPerDevice() {
        return sensorDataRepository.findLatestPerDevice();
    }

    public List<SensorReadingDto> getRecentReadings(int minutes) {
        return sensorDataRepository.findRecent(minutes, 1500);
    }

    public List<SensorReadingDto> getAnomalies() {
        return sensorDataRepository.findAnomalies(100);
    }
}

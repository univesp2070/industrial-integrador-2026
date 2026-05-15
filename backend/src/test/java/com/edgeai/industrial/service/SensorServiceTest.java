package com.edgeai.industrial.service;

import com.edgeai.industrial.domain.Device;
import com.edgeai.industrial.dto.SensorPayloadDto;
import com.edgeai.industrial.repository.SensorDataRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class SensorServiceTest {

    @Mock
    private SensorDataRepository sensorDataRepository;

    @Mock
    private PickService pickService;

    @InjectMocks
    private SensorService sensorService;

    private Device makeDevice() {
        Device device = new Device();
        device.setId(UUID.randomUUID());
        device.setName("esp32-sim-001");
        return device;
    }

    private SensorPayloadDto makePayload(boolean withWeight, boolean withPickEvent) {
        SensorPayloadDto payload = new SensorPayloadDto();
        payload.setDeviceId("esp32-sim-001");
        payload.setTimestamp(Instant.now());

        SensorPayloadDto.Sensors sensors = new SensorPayloadDto.Sensors();

        SensorPayloadDto.SensorValue temp = new SensorPayloadDto.SensorValue();
        temp.setValue(25.0); temp.setUnit("C");

        SensorPayloadDto.SensorValue vib = new SensorPayloadDto.SensorValue();
        vib.setValue(0.1); vib.setUnit("mm_s");

        SensorPayloadDto.SensorValue curr = new SensorPayloadDto.SensorValue();
        curr.setValue(2.0); curr.setUnit("A");

        sensors.setTemperature(temp);
        sensors.setVibration(vib);
        sensors.setCurrent(curr);

        if (withWeight) {
            SensorPayloadDto.SensorValue weight = new SensorPayloadDto.SensorValue();
            weight.setValue(4.75); weight.setUnit("kg");
            sensors.setWeight(weight);
        }

        payload.setSensors(sensors);

        SensorPayloadDto.Inference inference = new SensorPayloadDto.Inference();
        inference.setClassification("normal");
        inference.setAnomalyScore(0.05);
        payload.setInference(inference);

        if (withPickEvent) {
            SensorPayloadDto.PickEvent pick = new SensorPayloadDto.PickEvent();
            pick.setDetected(true);
            pick.setProductName("Parafuso M8");
            pick.setQuantity(3);
            pick.setWeightDeltaKg(0.075);
            pick.setConfidence(0.92);
            payload.setPickEvent(pick);
        }

        return payload;
    }

    @Test
    void saveSensorPayloadInsertsFourRowsWithWeight() {
        Device device = makeDevice();
        SensorPayloadDto payload = makePayload(true, false);

        sensorService.saveSensorPayload(device, payload);

        // temperature + vibration + current + weight = 4
        verify(sensorDataRepository, times(4)).insert(
                any(), eq(device.getId()), eq(device.getName()),
                any(), anyDouble(), any(), eq("normal"), eq(0.05)
        );
        verifyNoInteractions(pickService);
    }

    @Test
    void saveSensorPayloadInsertsThreeRowsWithoutWeight() {
        Device device = makeDevice();
        SensorPayloadDto payload = makePayload(false, false);

        sensorService.saveSensorPayload(device, payload);

        verify(sensorDataRepository, times(3)).insert(
                any(), eq(device.getId()), eq(device.getName()),
                any(), anyDouble(), any(), eq("normal"), eq(0.05)
        );
        verifyNoInteractions(pickService);
    }

    @Test
    void saveSensorPayloadSavesPickEventWhenDetected() {
        Device device = makeDevice();
        SensorPayloadDto payload = makePayload(true, true);

        sensorService.saveSensorPayload(device, payload);

        verify(pickService, times(1)).savePickEvent(
                eq(device.getId()),
                any(OffsetDateTime.class),
                eq(payload.getPickEvent())
        );
    }
}

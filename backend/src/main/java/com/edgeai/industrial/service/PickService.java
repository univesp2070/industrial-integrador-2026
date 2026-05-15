package com.edgeai.industrial.service;

import com.edgeai.industrial.dto.PickEventDto;
import com.edgeai.industrial.dto.ProductDemandDto;
import com.edgeai.industrial.dto.SensorPayloadDto;
import com.edgeai.industrial.repository.PickEventRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class PickService {

    private final PickEventRepository pickEventRepository;

    public void savePickEvent(UUID deviceId, OffsetDateTime time, SensorPayloadDto.PickEvent pick) {
        pickEventRepository.save(deviceId, time, pick);
    }

    public List<PickEventDto> getRecentPicks(int hours) {
        return pickEventRepository.findRecent(hours, 200);
    }

    public List<ProductDemandDto> getProductDemand(int hours) {
        return pickEventRepository.findDemandAggregate(hours);
    }
}

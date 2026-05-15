package com.edgeai.industrial.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import java.time.OffsetDateTime;

@Data
@AllArgsConstructor
public class ProductDemandDto {
    private String productName;
    private long totalPicks;
    private long totalQuantity;
    private OffsetDateTime lastPick;
}

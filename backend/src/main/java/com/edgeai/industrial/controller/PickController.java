package com.edgeai.industrial.controller;

import com.edgeai.industrial.dto.PickEventDto;
import com.edgeai.industrial.dto.ProductDemandDto;
import com.edgeai.industrial.service.PickService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/picks")
@CrossOrigin(origins = "*")
@RequiredArgsConstructor
public class PickController {

    private final PickService pickService;

    @GetMapping("/recent")
    public ResponseEntity<List<PickEventDto>> getRecent(
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(pickService.getRecentPicks(hours));
    }

    @GetMapping("/demand")
    public ResponseEntity<List<ProductDemandDto>> getDemand(
            @RequestParam(defaultValue = "168") int hours) {
        return ResponseEntity.ok(pickService.getProductDemand(hours));
    }
}

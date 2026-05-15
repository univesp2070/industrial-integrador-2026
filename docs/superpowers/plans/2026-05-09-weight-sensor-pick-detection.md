# Weight Sensor & Pick Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a weight sensor to the ESP32, detect product pick events via edge classification, persist them in a dedicated `pick_events` hypertable, and display a demand chart + event table in the dashboard.

**Architecture:** The ESP32 reads weight from a potentiometer (A6), detects drops > 50 g as pick events, classifies the product by matching the weight delta against a hardcoded catalog, and includes an optional `pick_event` field in the existing MQTT payload. The Spring Boot backend deserializes the new field, inserts weight into the existing `sensor_data` table, saves picks to a new `pick_events` hypertable, and exposes two new REST endpoints. The Next.js frontend adds a `/dashboard/picks` page with a BarChart and event table.

**Tech Stack:** Java 21 · Spring Boot 3.3 · JdbcTemplate · TimescaleDB · Arduino C++ · Next.js 15 · Recharts · Lombok · JUnit5 · Mockito · AssertJ

---

## File Map

| File | Action |
|------|--------|
| `database/migrations/V003__pick_events.sql` | Create |
| `backend/.../dto/SensorPayloadDto.java` | Modify — add `weight` to Sensors, add `PickEvent` nested class |
| `backend/.../dto/PickEventDto.java` | Create |
| `backend/.../dto/ProductDemandDto.java` | Create |
| `backend/.../repository/PickEventRepository.java` | Create |
| `backend/.../service/PickService.java` | Create |
| `backend/.../service/SensorService.java` | Modify — insert weight, call PickService |
| `backend/.../controller/PickController.java` | Create |
| `backend/src/test/.../dto/SensorPayloadDtoTest.java` | Modify — add weight + pick_event cases |
| `backend/src/test/.../service/SensorServiceTest.java` | Modify — 4 inserts, pickService call |
| `frontend/src/types/index.ts` | Modify — add PickEvent, ProductDemand |
| `frontend/src/services/apiClient.ts` | Modify — add getRecentPicks, getProductDemand |
| `frontend/src/components/DemandChart.tsx` | Create |
| `frontend/src/components/PickEventTable.tsx` | Create |
| `frontend/src/app/dashboard/picks/page.tsx` | Create |
| `frontend/src/app/dashboard/layout.tsx` | Modify — add nav link |
| `wokwi/diagram.json` | Modify — add pot3 for weight |
| `wokwi/sketch.ino` | Modify — weight reading + pick detection |

---

### Task 1: Database migration — pick_events hypertable

**Files:**
- Create: `database/migrations/V003__pick_events.sql`

- [ ] **Step 1: Create the migration file**

```sql
-- V003 - Pick events table
-- Records each product retrieval detected by weight sensor

CREATE TABLE IF NOT EXISTS pick_events (
    id              UUID NOT NULL DEFAULT gen_random_uuid(),
    time            TIMESTAMPTZ NOT NULL,
    device_id       UUID NOT NULL REFERENCES devices(id),
    product_name    TEXT NOT NULL,
    quantity        INT NOT NULL,
    weight_delta_kg FLOAT NOT NULL,
    confidence      FLOAT NOT NULL,
    PRIMARY KEY (id, time)  -- composite PK required by TimescaleDB (partition column must be in PK)
);

SELECT create_hypertable('pick_events', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_pick_events_device ON pick_events (device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_pick_events_product ON pick_events (product_name, time DESC);
```

- [ ] **Step 2: Apply migration to running Docker DB**

```powershell
$sql = Get-Content "database\migrations\V003__pick_events.sql" -Raw
docker exec -i edgeai-postgres psql -U edgeai -d edgeai -c $sql
```

Expected output contains: `CREATE TABLE`, `create_hypertable`, `CREATE INDEX`

- [ ] **Step 3: Verify table exists**

```powershell
docker exec edgeai-postgres psql -U edgeai -d edgeai -c "\d pick_events"
```

Expected: table columns listed (id, time, device_id, product_name, quantity, weight_delta_kg, confidence)

- [ ] **Step 4: Commit**

```powershell
git add database/migrations/V003__pick_events.sql
git commit -m "feat(db): add pick_events hypertable migration"
```

---

### Task 2: Update SensorPayloadDto — weight sensor + PickEvent nested class

**Files:**
- Modify: `backend/src/main/java/com/edgeai/industrial/dto/SensorPayloadDto.java`

- [ ] **Step 1: Add `weight` to Sensors and add `PickEvent` nested class**

Replace the full file content:

```java
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
```

- [ ] **Step 2: Run existing DTO test to confirm it still passes**

```powershell
cd backend
./gradlew test --tests "com.edgeai.industrial.dto.SensorPayloadDtoTest" --info
```

Expected: BUILD SUCCESSFUL, 1 test passed

---

### Task 3: Test SensorPayloadDto — weight and pick_event deserialization

**Files:**
- Modify: `backend/src/test/java/com/edgeai/industrial/dto/SensorPayloadDtoTest.java`

- [ ] **Step 1: Add two new test methods to SensorPayloadDtoTest**

Add after the existing `deserializesMqttSensorPayload` method:

```java
@Test
void deserializesWeightSensor() throws Exception {
    String json = """
            {
              "device_id": "wokwi-shelf-001",
              "timestamp": "2026-05-09T10:00:00Z",
              "sensors": {
                "temperature": {"value": 25.0, "unit": "C"},
                "vibration":   {"value": 0.1,  "unit": "mm_s"},
                "current":     {"value": 2.0,  "unit": "A"},
                "weight":      {"value": 4.75, "unit": "kg"}
              },
              "inference": {
                "classification": "normal",
                "anomaly_score": 0.05,
                "model_version": "wokwi-v1"
              }
            }
            """;

    SensorPayloadDto dto = mapper.readValue(json, SensorPayloadDto.class);

    assertThat(dto.getSensors().getWeight()).isNotNull();
    assertThat(dto.getSensors().getWeight().getValue()).isEqualTo(4.75);
    assertThat(dto.getSensors().getWeight().getUnit()).isEqualTo("kg");
    assertThat(dto.getPickEvent()).isNull();
}

@Test
void deserializesPickEvent() throws Exception {
    String json = """
            {
              "device_id": "wokwi-shelf-001",
              "timestamp": "2026-05-09T10:01:00Z",
              "sensors": {
                "temperature": {"value": 25.0, "unit": "C"},
                "vibration":   {"value": 0.1,  "unit": "mm_s"},
                "current":     {"value": 2.0,  "unit": "A"},
                "weight":      {"value": 4.675,"unit": "kg"}
              },
              "inference": {
                "classification": "normal",
                "anomaly_score": 0.05,
                "model_version": "wokwi-v1"
              },
              "pick_event": {
                "detected": true,
                "product_name": "Parafuso M8",
                "quantity": 3,
                "weight_delta_kg": 0.075,
                "confidence": 0.92
              }
            }
            """;

    SensorPayloadDto dto = mapper.readValue(json, SensorPayloadDto.class);

    assertThat(dto.getPickEvent()).isNotNull();
    assertThat(dto.getPickEvent().isDetected()).isTrue();
    assertThat(dto.getPickEvent().getProductName()).isEqualTo("Parafuso M8");
    assertThat(dto.getPickEvent().getQuantity()).isEqualTo(3);
    assertThat(dto.getPickEvent().getWeightDeltaKg()).isEqualTo(0.075);
    assertThat(dto.getPickEvent().getConfidence()).isEqualTo(0.92);
}
```

- [ ] **Step 2: Run all DTO tests**

```powershell
./gradlew test --tests "com.edgeai.industrial.dto.SensorPayloadDtoTest" --info
```

Expected: BUILD SUCCESSFUL, 3 tests passed

- [ ] **Step 3: Commit**

```powershell
git add backend/src/main/java/com/edgeai/industrial/dto/SensorPayloadDto.java
git add backend/src/test/java/com/edgeai/industrial/dto/SensorPayloadDtoTest.java
git commit -m "feat(backend): add weight sensor and PickEvent to SensorPayloadDto"
```

---

### Task 4: Create PickEventDto and ProductDemandDto

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/dto/PickEventDto.java`
- Create: `backend/src/main/java/com/edgeai/industrial/dto/ProductDemandDto.java`

- [ ] **Step 1: Create PickEventDto.java**

```java
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
```

- [ ] **Step 2: Create ProductDemandDto.java**

```java
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
```

- [ ] **Step 3: Compile check**

```powershell
./gradlew compileJava
```

Expected: BUILD SUCCESSFUL

---

### Task 5: Create PickEventRepository

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/repository/PickEventRepository.java`

- [ ] **Step 1: Create PickEventRepository.java**

```java
package com.edgeai.industrial.repository;

import com.edgeai.industrial.dto.PickEventDto;
import com.edgeai.industrial.dto.ProductDemandDto;
import com.edgeai.industrial.dto.SensorPayloadDto;
import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;

@Repository
@RequiredArgsConstructor
public class PickEventRepository {

    private final JdbcTemplate jdbc;

    public void save(UUID deviceId, OffsetDateTime time, SensorPayloadDto.PickEvent pick) {
        jdbc.update("""
                INSERT INTO pick_events
                    (time, device_id, product_name, quantity, weight_delta_kg, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                Timestamp.from(time.toInstant()),
                deviceId,
                pick.getProductName(),
                pick.getQuantity(),
                pick.getWeightDeltaKg(),
                pick.getConfidence());
    }

    public List<PickEventDto> findRecent(int hours, int limit) {
        return jdbc.query("""
                SELECT pe.time, pe.device_id, d.name AS device_name,
                       pe.product_name, pe.quantity, pe.weight_delta_kg, pe.confidence
                FROM pick_events pe
                JOIN devices d ON d.id = pe.device_id
                WHERE pe.time >= NOW() - (? * INTERVAL '1 hour')
                ORDER BY pe.time DESC
                LIMIT ?
                """,
                pickEventRowMapper(), hours, limit);
    }

    public List<ProductDemandDto> findDemandAggregate(int hours) {
        return jdbc.query("""
                SELECT product_name,
                       COUNT(*)       AS total_picks,
                       SUM(quantity)  AS total_quantity,
                       MAX(time)      AS last_pick
                FROM pick_events
                WHERE time >= NOW() - (? * INTERVAL '1 hour')
                GROUP BY product_name
                ORDER BY total_picks DESC
                """,
                demandRowMapper(), hours);
    }

    private RowMapper<PickEventDto> pickEventRowMapper() {
        return (rs, rowNum) -> new PickEventDto(
                rs.getTimestamp("time").toInstant().atOffset(ZoneOffset.UTC),
                UUID.fromString(rs.getString("device_id")),
                rs.getString("device_name"),
                rs.getString("product_name"),
                rs.getInt("quantity"),
                rs.getDouble("weight_delta_kg"),
                rs.getDouble("confidence")
        );
    }

    private RowMapper<ProductDemandDto> demandRowMapper() {
        return (rs, rowNum) -> new ProductDemandDto(
                rs.getString("product_name"),
                rs.getLong("total_picks"),
                rs.getLong("total_quantity"),
                rs.getTimestamp("last_pick").toInstant().atOffset(ZoneOffset.UTC)
        );
    }
}
```

- [ ] **Step 2: Compile check**

```powershell
./gradlew compileJava
```

Expected: BUILD SUCCESSFUL

---

### Task 6: Create PickService

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/service/PickService.java`

- [ ] **Step 1: Create PickService.java**

```java
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
```

- [ ] **Step 2: Compile check**

```powershell
./gradlew compileJava
```

Expected: BUILD SUCCESSFUL

---

### Task 7: Update SensorService — insert weight + call PickService

**Files:**
- Modify: `backend/src/main/java/com/edgeai/industrial/service/SensorService.java`

- [ ] **Step 1: Replace SensorService.java with updated version**

```java
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
```

- [ ] **Step 2: Run existing SensorService test — it should FAIL (still expects 3 inserts)**

```powershell
./gradlew test --tests "com.edgeai.industrial.service.SensorServiceTest" --info
```

Expected: FAIL — `Wanted 3 times but was 4 times` (or similar Mockito error, because `PickService` mock is null without `@Mock`)

---

### Task 8: Update SensorServiceTest

**Files:**
- Modify: `backend/src/test/java/com/edgeai/industrial/service/SensorServiceTest.java`

- [ ] **Step 1: Replace SensorServiceTest.java with updated version**

```java
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
```

- [ ] **Step 2: Run SensorService tests**

```powershell
./gradlew test --tests "com.edgeai.industrial.service.SensorServiceTest" --info
```

Expected: BUILD SUCCESSFUL, 3 tests passed

- [ ] **Step 3: Run all backend tests**

```powershell
./gradlew test --info
```

Expected: BUILD SUCCESSFUL, all tests pass

- [ ] **Step 4: Commit**

```powershell
git add backend/src/main/java/com/edgeai/industrial/dto/PickEventDto.java
git add backend/src/main/java/com/edgeai/industrial/dto/ProductDemandDto.java
git add backend/src/main/java/com/edgeai/industrial/repository/PickEventRepository.java
git add backend/src/main/java/com/edgeai/industrial/service/PickService.java
git add backend/src/main/java/com/edgeai/industrial/service/SensorService.java
git add backend/src/test/java/com/edgeai/industrial/service/SensorServiceTest.java
git commit -m "feat(backend): add PickService, PickEventRepository, weight insert to SensorService"
```

---

### Task 9: Create PickController

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/controller/PickController.java`

- [ ] **Step 1: Create PickController.java**

```java
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
```

- [ ] **Step 2: Boot the backend and test the endpoints manually**

```powershell
# In one terminal:
cd backend; ./gradlew bootRun

# In another terminal, after startup:
$token = (Invoke-RestMethod -Uri "http://localhost:8082/api/auth/login" `
  -Method POST -ContentType "application/json" `
  -Body '{"email":"admin@edgeai.local","password":"admin123"}').token

Invoke-RestMethod -Uri "http://localhost:8082/api/picks/recent" `
  -Headers @{Authorization="Bearer $token"}

Invoke-RestMethod -Uri "http://localhost:8082/api/picks/demand" `
  -Headers @{Authorization="Bearer $token"}
```

Expected: both return `[]` (empty array — no picks yet)

- [ ] **Step 3: Commit**

```powershell
git add backend/src/main/java/com/edgeai/industrial/controller/PickController.java
git commit -m "feat(backend): add PickController with /api/picks/recent and /api/picks/demand"
```

---

### Task 10: Frontend types

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add PickEvent and ProductDemand interfaces**

Append to the end of `frontend/src/types/index.ts`:

```typescript
export interface PickEvent {
  time: string;
  deviceId: string;
  deviceName: string;
  productName: string;
  quantity: number;
  weightDeltaKg: number;
  confidence: number;
}

export interface ProductDemand {
  productName: string;
  totalPicks: number;
  totalQuantity: number;
  lastPick: string;
}
```

Also update `SensorReading.sensorType` to include `'weight'`:

```typescript
// Change:
sensorType: 'temperature' | 'vibration' | 'current';
// To:
sensorType: 'temperature' | 'vibration' | 'current' | 'weight';
```

---

### Task 11: Frontend apiClient

**Files:**
- Modify: `frontend/src/services/apiClient.ts`

- [ ] **Step 1: Add getRecentPicks and getProductDemand**

Add two entries to the `apiClient` object (after the existing `getAnomalies` line):

```typescript
getRecentPicks: (hours = 24) =>
  request<import('@/types').PickEvent[]>(`/picks/recent?hours=${hours}`),
getProductDemand: (hours = 168) =>
  request<import('@/types').ProductDemand[]>(`/picks/demand?hours=${hours}`),
```

---

### Task 12: DemandChart component

**Files:**
- Create: `frontend/src/components/DemandChart.tsx`

- [ ] **Step 1: Create DemandChart.tsx**

```tsx
'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { ProductDemand } from '@/types';

interface DemandChartProps {
  demand: ProductDemand[];
}

export function DemandChart({ demand }: DemandChartProps) {
  if (demand.length === 0) {
    return (
      <p className="text-gray-400 text-sm">Nenhuma retirada registrada ainda.</p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={demand} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="productName" stroke="#9ca3af" tick={{ fontSize: 11 }} />
        <YAxis stroke="#9ca3af" tick={{ fontSize: 11 }} allowDecimals={false} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
          labelStyle={{ color: '#e5e7eb' }}
          formatter={(value: number) => [value, 'Retiradas']}
        />
        <Bar dataKey="totalPicks" name="Retiradas" fill="#6366f1" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

---

### Task 13: PickEventTable component

**Files:**
- Create: `frontend/src/components/PickEventTable.tsx`

- [ ] **Step 1: Create PickEventTable.tsx**

```tsx
'use client';

import { PickEvent } from '@/types';

interface PickEventTableProps {
  picks: PickEvent[];
}

export function PickEventTable({ picks }: PickEventTableProps) {
  if (picks.length === 0) {
    return (
      <p className="text-gray-400 text-sm">Nenhuma retirada nas últimas 24 horas.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="border-b border-gray-700 text-gray-400 text-xs uppercase tracking-wider">
            <th className="py-2 pr-4">Horário</th>
            <th className="py-2 pr-4">Dispositivo</th>
            <th className="py-2 pr-4">Produto</th>
            <th className="py-2 pr-4">Qtd</th>
            <th className="py-2 pr-4">Peso retirado</th>
            <th className="py-2">Confiança</th>
          </tr>
        </thead>
        <tbody>
          {picks.map((p, i) => {
            const confPercent = (p.confidence * 100).toFixed(0);
            const isHigh = p.confidence >= 0.85;
            return (
              <tr key={i} className="border-b border-gray-700 hover:bg-gray-800">
                <td className="py-2 pr-4 text-gray-300">
                  {new Date(p.time).toLocaleString('pt-BR')}
                </td>
                <td className="py-2 pr-4 text-gray-300">{p.deviceName}</td>
                <td className="py-2 pr-4 text-gray-300">{p.productName}</td>
                <td className="py-2 pr-4 text-gray-300">{p.quantity}</td>
                <td className="py-2 pr-4 text-gray-300">
                  {(p.weightDeltaKg * 1000).toFixed(0)} g
                </td>
                <td className="py-2">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                      isHigh
                        ? 'bg-green-900 text-green-300'
                        : 'bg-yellow-900 text-yellow-300'
                    }`}
                  >
                    {confPercent}%
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```

---

### Task 14: Picks dashboard page

**Files:**
- Create: `frontend/src/app/dashboard/picks/page.tsx`

- [ ] **Step 1: Create picks/page.tsx**

```tsx
'use client';

import { useState } from 'react';
import { PickEvent, ProductDemand } from '@/types';
import { apiClient } from '@/services/apiClient';
import { usePolling } from '@/hooks/usePolling';
import { DemandChart } from '@/components/DemandChart';
import { PickEventTable } from '@/components/PickEventTable';

export default function PicksPage() {
  const [picks, setPicks] = useState<PickEvent[]>([]);
  const [demand, setDemand] = useState<ProductDemand[]>([]);
  const [loading, setLoading] = useState(true);

  usePolling(() => {
    Promise.all([
      apiClient.getRecentPicks(24),
      apiClient.getProductDemand(168),
    ])
      .then(([picksData, demandData]) => {
        setPicks(picksData);
        setDemand(demandData);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, 10000);

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6 text-white">Retiradas de Produtos</h1>

      {loading ? (
        <p className="text-gray-400 text-sm">Carregando dados...</p>
      ) : (
        <div className="flex flex-col gap-6">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h2 className="text-sm text-gray-400 mb-4">
              Demanda por produto — últimos 7 dias
            </h2>
            <DemandChart demand={demand} />
          </div>

          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h2 className="text-sm text-gray-400 mb-4">
              Eventos de retirada — últimas 24h
            </h2>
            <PickEventTable picks={picks} />
          </div>
        </div>
      )}
    </div>
  );
}
```

---

### Task 15: Add nav link + commit frontend

**Files:**
- Modify: `frontend/src/app/dashboard/layout.tsx`

- [ ] **Step 1: Add Retiradas link to nav**

In `frontend/src/app/dashboard/layout.tsx`, add after the Anomalias link:

```tsx
<Link href="/dashboard/picks" className="text-sm text-gray-300 hover:text-white py-1">
  Retiradas
</Link>
```

- [ ] **Step 2: Start dev server and verify the page renders**

```powershell
cd frontend
npm run dev
```

Open http://localhost:3000/dashboard/picks — should show "Retiradas de Produtos" page with empty state messages.

- [ ] **Step 3: Commit frontend**

```powershell
git add frontend/src/types/index.ts
git add frontend/src/services/apiClient.ts
git add frontend/src/components/DemandChart.tsx
git add frontend/src/components/PickEventTable.tsx
git add frontend/src/app/dashboard/picks/page.tsx
git add frontend/src/app/dashboard/layout.tsx
git commit -m "feat(frontend): add picks page with DemandChart and PickEventTable"
```

---

### Task 16: Wokwi — add pot3 for weight sensor

**Files:**
- Modify: `wokwi/diagram.json`

- [ ] **Step 1: Add pot3 to parts and connections in diagram.json**

In `wokwi/diagram.json`, add to `"parts"` array:

```json
{ "type": "wokwi-potentiometer", "id": "pot3", "top": 340, "left": 260, "attrs": { "label": "Weight (kg)", "value": "0.5" } }
```

Add to `"connections"` array:

```json
[ "pot3:VCC", "esp:3V3", "red", [] ],
[ "pot3:GND", "esp:GND.2", "black", [] ],
[ "pot3:SIG", "esp:A6", "purple", [] ]
```

---

### Task 17: Wokwi sketch — weight reading + pick detection

**Files:**
- Modify: `wokwi/sketch.ino`

- [ ] **Step 1: Add weight pin constant and product catalog**

After the existing pin definitions (`#define LED_ANOMALY  5`), add:

```cpp
#define WEIGHT_PIN   A6
```

After the existing threshold constants (`const float PUBLISH_SEC   = 5.0;`), add:

```cpp
const float WEIGHT_MAX_KG  = 10.0f;
const float PICK_THRESHOLD = 0.050f;  // 50g minimum to count as a pick

struct Product { const char* name; float unit_kg; float tolerance_kg; };
const Product CATALOG[] = {
  { "Parafuso M8",  0.025f, 0.008f },
  { "Porca M8",     0.010f, 0.004f },
  { "Arruela M8",   0.005f, 0.002f },
  { "Parafuso M12", 0.060f, 0.015f },
};
const int CATALOG_SIZE = 4;
```

- [ ] **Step 2: Add readWeight() helper and classifyPick() function**

After the existing `calcAnomalyScore()` function, add:

```cpp
float readWeight() {
  int raw = analogRead(WEIGHT_PIN);
  return (raw / 4095.0f) * WEIGHT_MAX_KG;
}

struct PickResult { bool detected; const char* name; int qty; float delta; float conf; };

PickResult classifyPick(float prevWeight, float currentWeight) {
  float delta = prevWeight - currentWeight;
  if (delta < PICK_THRESHOLD) return { false, nullptr, 0, 0.0f, 0.0f };

  const Product* best = nullptr;
  float bestError = 1e9f;
  for (int i = 0; i < CATALOG_SIZE; i++) {
    int qty = max(1, (int)round(delta / CATALOG[i].unit_kg));
    float expected = qty * CATALOG[i].unit_kg;
    float error = fabsf(delta - expected);
    if (error < CATALOG[i].tolerance_kg * qty && error < bestError) {
      bestError = error;
      best = &CATALOG[i];
    }
  }

  if (!best) return { false, nullptr, 0, 0.0f, 0.0f };

  int qty = max(1, (int)round(delta / best->unit_kg));
  float expected = qty * best->unit_kg;
  float conf = constrain(1.0f - fabsf(delta - expected) / best->unit_kg, 0.0f, 1.0f);
  return { true, best->name, qty, delta, conf };
}
```

- [ ] **Step 3: Add prevWeight tracking variable and update loop()**

After the existing `unsigned long lastPublish = 0;` global, add:

```cpp
float prevWeight = -1.0f;
```

In the `loop()` function, after reading the existing sensors (`float cur = readCurrent();`), add:

```cpp
float weight = readWeight();
```

In the JSON payload section, after `JsonObject inf = doc.createNestedObject("inference");` block, before `char buf[512];`, add:

```cpp
JsonObject wgtObj = sensors.createNestedObject("weight");
wgtObj["value"] = round(weight * 1000) / 1000.0;
wgtObj["unit"]  = "kg";

// Pick detection
if (prevWeight >= 0.0f) {
  PickResult pick = classifyPick(prevWeight, weight);
  if (pick.detected) {
    JsonObject pe = doc.createNestedObject("pick_event");
    pe["detected"]        = true;
    pe["product_name"]    = pick.name;
    pe["quantity"]        = pick.qty;
    pe["weight_delta_kg"] = round(pick.delta * 10000) / 10000.0;
    pe["confidence"]      = round(pick.conf * 1000) / 1000.0;
    Serial.printf("[PICK] product=%s qty=%d delta=%.3fkg conf=%.2f\n",
                  pick.name, pick.qty, pick.delta, pick.conf);
  }
}
prevWeight = weight;
```

Also increase the `StaticJsonDocument` size from 512 to 768 to accommodate the extra fields:

```cpp
// Change:
StaticJsonDocument<512> doc;
// To:
StaticJsonDocument<768> doc;
```

And update `char buf[512]` to `char buf[768]`.

- [ ] **Step 4: Commit Wokwi files**

```powershell
git add wokwi/diagram.json wokwi/sketch.ino
git commit -m "feat(wokwi): add weight sensor pot3 and pick detection logic"
```

---

### Task 18: End-to-end smoke test

- [ ] **Step 1: Ensure infrastructure is running**

```powershell
docker compose ps
```

Expected: edgeai-postgres, edgeai-emqx, edgeai-kafka all healthy

- [ ] **Step 2: Start backend**

```powershell
cd backend; ./gradlew bootRun
```

Wait for `Started BackendApplication`

- [ ] **Step 3: Start frontend**

```powershell
cd frontend; npm run dev
```

- [ ] **Step 4: Inject a test pick event directly into the DB**

```powershell
# Get the device_id for wokwi-esp32-001 (must exist after at least one MQTT message)
$devId = docker exec edgeai-postgres psql -U edgeai -d edgeai -t -c `
  "SELECT id FROM devices WHERE name LIKE '%wokwi%' LIMIT 1;"

# If no device yet, insert one
docker exec edgeai-postgres psql -U edgeai -d edgeai -c `
  "INSERT INTO devices (name, device_type, status) VALUES ('wokwi-shelf-001','shelf','active') ON CONFLICT DO NOTHING;"

$devId = docker exec edgeai-postgres psql -U edgeai -d edgeai -t -c `
  "SELECT id FROM devices WHERE name='wokwi-shelf-001' LIMIT 1;"
$devId = $devId.Trim()

docker exec edgeai-postgres psql -U edgeai -d edgeai -c `
  "INSERT INTO pick_events (time, device_id, product_name, quantity, weight_delta_kg, confidence) VALUES (NOW(), '$devId', 'Parafuso M8', 3, 0.075, 0.92), (NOW() - INTERVAL '1 hour', '$devId', 'Porca M8', 5, 0.050, 0.88), (NOW() - INTERVAL '3 hours', '$devId', 'Parafuso M8', 2, 0.050, 0.95);"
```

- [ ] **Step 5: Verify endpoints**

```powershell
$token = (Invoke-RestMethod -Uri "http://localhost:8082/api/auth/login" `
  -Method POST -ContentType "application/json" `
  -Body '{"email":"admin@edgeai.local","password":"admin123"}').token

Invoke-RestMethod -Uri "http://localhost:8082/api/picks/recent" `
  -Headers @{Authorization="Bearer $token"} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8082/api/picks/demand" `
  -Headers @{Authorization="Bearer $token"} | ConvertTo-Json
```

Expected: `recent` returns 3 events; `demand` returns Parafuso M8 (2 picks) + Porca M8 (1 pick)

- [ ] **Step 6: Verify dashboard**

Open http://localhost:3000/dashboard/picks

Expected:
- Bar chart shows "Parafuso M8" and "Porca M8" bars
- Table shows 3 events with green/yellow confidence badges

- [ ] **Step 7: Final commit**

```powershell
git add -A
git commit -m "feat: weight sensor pick detection — end-to-end complete"
git push
```

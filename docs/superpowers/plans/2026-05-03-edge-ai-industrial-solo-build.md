# Edge AI Industrial — Solo Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o sistema completo de monitoramento industrial edge AI — firmware já pronto, este plano cobre backend Spring Boot, Kafka, JWT e dashboard Next.js — entregando um fluxo ponta-a-ponta documentável para o relatório UNIVESP PI-5 (prazo: 2026-06-30).

**Architecture:** Walking Skeleton first (MQTT → Backend direto → DB → Frontend), depois Kafka é inserido no meio sem quebrar nada, depois JWT. Cada fase entrega software funcional testável antes da próxima começar.

**Tech Stack:** Spring Boot 3.3 + Gradle, Spring Integration MQTT, Spring Kafka 3, JJWT 0.12.5, Spring Security 6, PostgreSQL + TimescaleDB, Next.js 15 App Router, React 19, Recharts, Tailwind CSS 3.

---

## Mapa de Arquivos

### Backend — criar
```
backend/src/main/java/com/edgeai/industrial/
├── domain/
│   ├── Device.java              — @Entity mapeando tabela devices
│   └── User.java                — @Entity mapeando tabela users (para JWT)
├── dto/
│   ├── SensorPayloadDto.java    — desserialização do payload MQTT sensor/data
│   ├── SensorReadingDto.java    — resposta REST de leitura de sensor
│   └── DeviceStatusDto.java     — desserialização do payload MQTT device/status
├── repository/
│   ├── DeviceRepository.java    — JpaRepository<Device, UUID>
│   ├── UserRepository.java      — JpaRepository<User, UUID>
│   └── SensorDataRepository.java — JdbcTemplate (sensor_data não tem PK simples)
├── service/
│   ├── DeviceService.java       — findOrCreate + updateLastSeen
│   └── SensorService.java       — saveSensorPayload + queries
├── mqtt/
│   ├── MqttConfig.java          — Spring Integration MQTT beans
│   └── MqttSubscriber.java      — @ServiceActivator, parseia e encaminha
├── kafka/                        — criado na Fase 2
│   ├── KafkaConfig.java
│   ├── SensorProducer.java
│   └── SensorConsumer.java
├── controller/
│   ├── DeviceController.java    — GET /api/devices
│   ├── SensorController.java    — GET /api/sensors/*
│   └── AuthController.java      — POST /api/auth/login (Fase 3)
├── security/                    — criado na Fase 3
│   ├── JwtService.java
│   ├── JwtFilter.java
│   ├── UserDetailsServiceImpl.java
│   └── SecurityConfig.java
└── config/
    └── SecurityConfig.java      — Fase 1: permite tudo; substituído na Fase 3
```

### Backend — modificar
```
backend/src/main/resources/application.yml   — adicionar config CORS e kafka topic
```

### Frontend — criar
```
frontend/
├── next.config.js
├── tailwind.config.js
├── postcss.config.js
└── src/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx                      — redirect para /dashboard
    │   ├── (auth)/login/page.tsx
    │   ├── dashboard/page.tsx            — cards de dispositivos
    │   ├── dashboard/readings/page.tsx   — gráfico de série temporal
    │   └── dashboard/anomalies/page.tsx  — tabela de anomalias
    ├── components/
    │   ├── DeviceCard.tsx
    │   ├── SensorChart.tsx               — Recharts LineChart
    │   └── AnomalyTable.tsx
    ├── services/
    │   └── apiClient.ts                  — fetch wrapper com JWT Bearer
    ├── hooks/
    │   └── usePolling.ts                 — polling a cada 10s
    └── types/
        └── index.ts                      — SensorReading, Device, AnomalyRecord
```

---

## FASE 1 — Walking Skeleton (04–17 mai)

> Objetivo: Simulador Python → MQTT → Backend (sem Kafka) → PostgreSQL → 1 gráfico no frontend funcionando.

---

### Task 1: Subir a infraestrutura e verificar

**Files:**
- None (docker-compose.yml já existe)

- [ ] **Step 1.1: Subir Docker Compose**

```bash
cd "C:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
docker compose up -d
```

- [ ] **Step 1.2: Verificar todos os serviços healthy**

```bash
docker compose ps
```

Esperado: todos os serviços com status `running` ou `healthy`. Se TimescaleDB der erro de extensão, aguardar 30s e repetir.

- [ ] **Step 1.3: Verificar schema no banco**

```bash
docker compose exec postgres psql -U edgeai -d edgeai -c "\dt"
```

Esperado: tabelas `devices`, `sensor_data`, `users`, `alerts` listadas.

- [ ] **Step 1.4: Commit**

```bash
git add .
git commit -m "chore: verify infrastructure stack is operational"
```

---

### Task 2: Criar entidades JPA — Device e User

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/domain/Device.java`
- Create: `backend/src/main/java/com/edgeai/industrial/domain/User.java`
- Create: `backend/src/test/java/com/edgeai/industrial/domain/DeviceTest.java`

- [ ] **Step 2.1: Escrever teste de sanidade da entidade Device**

Crie `backend/src/test/java/com/edgeai/industrial/domain/DeviceTest.java`:

```java
package com.edgeai.industrial.domain;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class DeviceTest {

    @Test
    void deviceIsOnlineWhenStatusIsOnline() {
        Device device = new Device();
        device.setStatus("online");
        assertThat(device.getStatus()).isEqualTo("online");
    }
}
```

- [ ] **Step 2.2: Rodar o teste — deve falhar pois Device não existe**

```bash
cd backend
./gradlew test --tests "com.edgeai.industrial.domain.DeviceTest" 2>&1 | tail -20
```

Esperado: `FAILED` — `cannot find symbol: class Device`

- [ ] **Step 2.3: Criar Device.java**

Crie `backend/src/main/java/com/edgeai/industrial/domain/Device.java`:

```java
package com.edgeai.industrial.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.OffsetDateTime;
import java.util.UUID;

@Data
@NoArgsConstructor
@Entity
@Table(name = "devices")
public class Device {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private String name;

    @Column(name = "device_type", nullable = false)
    private String deviceType;

    @Column(name = "firmware_version")
    private String firmwareVersion;

    private String location;

    @Column(columnDefinition = "VARCHAR(20) DEFAULT 'inactive'")
    private String status = "inactive";

    @Column(name = "last_seen_at")
    private OffsetDateTime lastSeenAt;

    @Column(name = "created_at", updatable = false)
    private OffsetDateTime createdAt = OffsetDateTime.now();

    @Column(name = "updated_at")
    private OffsetDateTime updatedAt = OffsetDateTime.now();

    @PreUpdate
    void onUpdate() {
        this.updatedAt = OffsetDateTime.now();
    }
}
```

- [ ] **Step 2.4: Criar User.java**

Crie `backend/src/main/java/com/edgeai/industrial/domain/User.java`:

```java
package com.edgeai.industrial.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.OffsetDateTime;
import java.util.UUID;

@Data
@NoArgsConstructor
@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(unique = true, nullable = false)
    private String email;

    @Column(name = "password_hash", nullable = false)
    private String passwordHash;

    @Column(nullable = false)
    private String name;

    @Column(columnDefinition = "VARCHAR(20) DEFAULT 'viewer'")
    private String role = "viewer";

    @Column(columnDefinition = "BOOLEAN DEFAULT TRUE")
    private Boolean active = true;

    @Column(name = "created_at", updatable = false)
    private OffsetDateTime createdAt = OffsetDateTime.now();

    @Column(name = "updated_at")
    private OffsetDateTime updatedAt = OffsetDateTime.now();
}
```

- [ ] **Step 2.5: Rodar o teste — deve passar**

```bash
./gradlew test --tests "com.edgeai.industrial.domain.DeviceTest"
```

Esperado: `PASSED`

- [ ] **Step 2.6: Commit**

```bash
git add backend/src/main/java/com/edgeai/industrial/domain/ \
        backend/src/test/java/com/edgeai/industrial/domain/
git commit -m "feat(backend): add Device and User JPA entities"
```

---

### Task 3: DTOs para payload MQTT e resposta REST

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/dto/SensorPayloadDto.java`
- Create: `backend/src/main/java/com/edgeai/industrial/dto/SensorReadingDto.java`
- Create: `backend/src/main/java/com/edgeai/industrial/dto/DeviceStatusDto.java`
- Create: `backend/src/test/java/com/edgeai/industrial/dto/SensorPayloadDtoTest.java`

- [ ] **Step 3.1: Escrever teste de desserialização do payload MQTT**

Crie `backend/src/test/java/com/edgeai/industrial/dto/SensorPayloadDtoTest.java`:

```java
package com.edgeai.industrial.dto;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class SensorPayloadDtoTest {

    private final ObjectMapper mapper = new ObjectMapper()
            .registerModule(new JavaTimeModule());

    @Test
    void deserializesMqttSensorPayload() throws Exception {
        String json = """
                {
                  "device_id": "esp32-sim-001",
                  "timestamp": "2026-05-03T12:00:00Z",
                  "sensors": {
                    "temperature": {"value": 45.2, "unit": "C"},
                    "vibration": {"value": 1.8, "unit": "mm_s"},
                    "current": {"value": 3.1, "unit": "A"}
                  },
                  "inference": {
                    "classification": "normal",
                    "anomaly_score": 0.12,
                    "model_version": "sim-v1"
                  }
                }
                """;

        SensorPayloadDto dto = mapper.readValue(json, SensorPayloadDto.class);

        assertThat(dto.getDeviceId()).isEqualTo("esp32-sim-001");
        assertThat(dto.getSensors().getTemperature().getValue()).isEqualTo(45.2);
        assertThat(dto.getInference().getClassification()).isEqualTo("normal");
        assertThat(dto.getInference().getAnomalyScore()).isEqualTo(0.12);
    }
}
```

- [ ] **Step 3.2: Rodar o teste — deve falhar**

```bash
./gradlew test --tests "com.edgeai.industrial.dto.SensorPayloadDtoTest"
```

Esperado: `FAILED` — classe não existe

- [ ] **Step 3.3: Criar SensorPayloadDto.java**

Crie `backend/src/main/java/com/edgeai/industrial/dto/SensorPayloadDto.java`:

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

    @Data
    public static class Sensors {
        private SensorValue temperature;
        private SensorValue vibration;
        private SensorValue current;
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
}
```

- [ ] **Step 3.4: Criar SensorReadingDto.java**

Crie `backend/src/main/java/com/edgeai/industrial/dto/SensorReadingDto.java`:

```java
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
```

- [ ] **Step 3.5: Criar DeviceStatusDto.java**

Crie `backend/src/main/java/com/edgeai/industrial/dto/DeviceStatusDto.java`:

```java
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
```

- [ ] **Step 3.6: Rodar o teste — deve passar**

```bash
./gradlew test --tests "com.edgeai.industrial.dto.SensorPayloadDtoTest"
```

Esperado: `PASSED`

- [ ] **Step 3.7: Commit**

```bash
git add backend/src/main/java/com/edgeai/industrial/dto/ \
        backend/src/test/java/com/edgeai/industrial/dto/
git commit -m "feat(backend): add MQTT payload and REST response DTOs"
```

---

### Task 4: Repositórios (JPA + JdbcTemplate)

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/repository/DeviceRepository.java`
- Create: `backend/src/main/java/com/edgeai/industrial/repository/UserRepository.java`
- Create: `backend/src/main/java/com/edgeai/industrial/repository/SensorDataRepository.java`

> Nota: `sensor_data` não tem coluna `id` (é hypertable TimescaleDB). Usar `JdbcTemplate` para operações nessa tabela.

- [ ] **Step 4.1: Criar DeviceRepository.java**

Crie `backend/src/main/java/com/edgeai/industrial/repository/DeviceRepository.java`:

```java
package com.edgeai.industrial.repository;

import com.edgeai.industrial.domain.Device;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import java.time.OffsetDateTime;
import java.util.Optional;
import java.util.UUID;

public interface DeviceRepository extends JpaRepository<Device, UUID> {

    Optional<Device> findByName(String name);

    @Modifying
    @Query("UPDATE Device d SET d.status = :status, d.lastSeenAt = :lastSeenAt, d.updatedAt = :updatedAt WHERE d.id = :id")
    void updateStatusAndLastSeen(UUID id, String status, OffsetDateTime lastSeenAt, OffsetDateTime updatedAt);
}
```

- [ ] **Step 4.2: Criar UserRepository.java**

Crie `backend/src/main/java/com/edgeai/industrial/repository/UserRepository.java`:

```java
package com.edgeai.industrial.repository;

import com.edgeai.industrial.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;
import java.util.UUID;

public interface UserRepository extends JpaRepository<User, UUID> {

    Optional<User> findByEmail(String email);
}
```

- [ ] **Step 4.3: Criar SensorDataRepository.java**

Crie `backend/src/main/java/com/edgeai/industrial/repository/SensorDataRepository.java`:

```java
package com.edgeai.industrial.repository;

import com.edgeai.industrial.dto.SensorReadingDto;
import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;
import java.sql.ResultSet;
import java.sql.Timestamp;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;

@Repository
@RequiredArgsConstructor
public class SensorDataRepository {

    private final JdbcTemplate jdbc;

    public void insert(OffsetDateTime time, UUID deviceId, String deviceName,
                       String sensorType, double value, String unit,
                       String classification, double anomalyScore) {
        jdbc.update("""
                INSERT INTO sensor_data
                    (time, device_id, sensor_type, value, unit, classification, anomaly_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                Timestamp.from(time.toInstant()), deviceId, sensorType,
                value, unit, classification, anomalyScore);
    }

    public List<SensorReadingDto> findByDeviceAndTimeRange(UUID deviceId,
                                                           OffsetDateTime from,
                                                           OffsetDateTime to) {
        return jdbc.query("""
                SELECT sd.time, sd.device_id, d.name AS device_name,
                       sd.sensor_type, sd.value, sd.unit,
                       sd.classification, sd.anomaly_score
                FROM sensor_data sd
                JOIN devices d ON d.id = sd.device_id
                WHERE sd.device_id = ?
                  AND sd.time BETWEEN ? AND ?
                ORDER BY sd.time DESC
                LIMIT 500
                """,
                rowMapper(),
                deviceId,
                Timestamp.from(from.toInstant()),
                Timestamp.from(to.toInstant()));
    }

    public List<SensorReadingDto> findLatestPerDevice() {
        return jdbc.query("""
                SELECT DISTINCT ON (sd.device_id)
                    sd.time, sd.device_id, d.name AS device_name,
                    sd.sensor_type, sd.value, sd.unit,
                    sd.classification, sd.anomaly_score
                FROM sensor_data sd
                JOIN devices d ON d.id = sd.device_id
                ORDER BY sd.device_id, sd.time DESC
                """,
                rowMapper());
    }

    public List<SensorReadingDto> findAnomalies(int limit) {
        return jdbc.query("""
                SELECT sd.time, sd.device_id, d.name AS device_name,
                       sd.sensor_type, sd.value, sd.unit,
                       sd.classification, sd.anomaly_score
                FROM sensor_data sd
                JOIN devices d ON d.id = sd.device_id
                WHERE sd.classification = 'anomaly'
                ORDER BY sd.time DESC
                LIMIT ?
                """,
                rowMapper(), limit);
    }

    private RowMapper<SensorReadingDto> rowMapper() {
        return (rs, rowNum) -> new SensorReadingDto(
                rs.getTimestamp("time").toInstant().atOffset(ZoneOffset.UTC),
                UUID.fromString(rs.getString("device_id")),
                rs.getString("device_name"),
                rs.getString("sensor_type"),
                rs.getDouble("value"),
                rs.getString("unit"),
                rs.getString("classification"),
                rs.getDouble("anomaly_score")
        );
    }
}
```

- [ ] **Step 4.4: Commit**

```bash
git add backend/src/main/java/com/edgeai/industrial/repository/
git commit -m "feat(backend): add repositories — JPA for Device/User, JdbcTemplate for sensor_data"
```

---

### Task 5: Services — DeviceService e SensorService

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/service/DeviceService.java`
- Create: `backend/src/main/java/com/edgeai/industrial/service/SensorService.java`
- Create: `backend/src/test/java/com/edgeai/industrial/service/SensorServiceTest.java`

- [ ] **Step 5.1: Escrever teste do SensorService**

Crie `backend/src/test/java/com/edgeai/industrial/service/SensorServiceTest.java`:

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
import java.util.UUID;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

@ExtendWith(MockitoExtension.class)
class SensorServiceTest {

    @Mock
    private SensorDataRepository sensorDataRepository;

    @InjectMocks
    private SensorService sensorService;

    @Test
    void saveSensorPayloadInsertsThreeRows() {
        Device device = new Device();
        device.setId(UUID.randomUUID());
        device.setName("esp32-sim-001");

        SensorPayloadDto payload = new SensorPayloadDto();
        payload.setDeviceId("esp32-sim-001");
        payload.setTimestamp(Instant.now());

        SensorPayloadDto.Sensors sensors = new SensorPayloadDto.Sensors();
        SensorPayloadDto.SensorValue temp = new SensorPayloadDto.SensorValue();
        temp.setValue(45.2);
        temp.setUnit("C");
        SensorPayloadDto.SensorValue vib = new SensorPayloadDto.SensorValue();
        vib.setValue(1.8);
        vib.setUnit("mm_s");
        SensorPayloadDto.SensorValue curr = new SensorPayloadDto.SensorValue();
        curr.setValue(3.1);
        curr.setUnit("A");
        sensors.setTemperature(temp);
        sensors.setVibration(vib);
        sensors.setCurrent(curr);
        payload.setSensors(sensors);

        SensorPayloadDto.Inference inference = new SensorPayloadDto.Inference();
        inference.setClassification("normal");
        inference.setAnomalyScore(0.12);
        payload.setInference(inference);

        sensorService.saveSensorPayload(device, payload);

        // 3 sensores = 3 inserções
        verify(sensorDataRepository, times(3)).insert(
                any(), eq(device.getId()), eq(device.getName()),
                any(), anyDouble(), any(), eq("normal"), eq(0.12)
        );
    }
}
```

- [ ] **Step 5.2: Rodar o teste — deve falhar**

```bash
./gradlew test --tests "com.edgeai.industrial.service.SensorServiceTest"
```

Esperado: `FAILED` — classe não existe

- [ ] **Step 5.3: Criar DeviceService.java**

Crie `backend/src/main/java/com/edgeai/industrial/service/DeviceService.java`:

```java
package com.edgeai.industrial.service;

import com.edgeai.industrial.domain.Device;
import com.edgeai.industrial.repository.DeviceRepository;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.OffsetDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class DeviceService {

    private final DeviceRepository deviceRepository;

    @Transactional
    public Device findOrCreate(String deviceId, String firmwareVersion) {
        return deviceRepository.findByName(deviceId).orElseGet(() -> {
            Device device = new Device();
            device.setName(deviceId);
            device.setDeviceType("esp32");
            device.setFirmwareVersion(firmwareVersion);
            device.setStatus("online");
            device.setLastSeenAt(OffsetDateTime.now());
            return deviceRepository.save(device);
        });
    }

    @Transactional
    public void markOnline(Device device) {
        deviceRepository.updateStatusAndLastSeen(
                device.getId(), "online",
                OffsetDateTime.now(), OffsetDateTime.now()
        );
    }

    @Transactional
    public void markOffline(String deviceName) {
        deviceRepository.findByName(deviceName).ifPresent(device ->
                deviceRepository.updateStatusAndLastSeen(
                        device.getId(), "offline",
                        OffsetDateTime.now(), OffsetDateTime.now()
                )
        );
    }

    public List<Device> listAll() {
        return deviceRepository.findAll();
    }
}
```

- [ ] **Step 5.4: Criar SensorService.java**

Crie `backend/src/main/java/com/edgeai/industrial/service/SensorService.java`:

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
    }

    public List<SensorReadingDto> getReadings(UUID deviceId, OffsetDateTime from, OffsetDateTime to) {
        return sensorDataRepository.findByDeviceAndTimeRange(deviceId, from, to);
    }

    public List<SensorReadingDto> getLatestPerDevice() {
        return sensorDataRepository.findLatestPerDevice();
    }

    public List<SensorReadingDto> getAnomalies() {
        return sensorDataRepository.findAnomalies(100);
    }
}
```

- [ ] **Step 5.5: Rodar o teste — deve passar**

```bash
./gradlew test --tests "com.edgeai.industrial.service.SensorServiceTest"
```

Esperado: `PASSED`

- [ ] **Step 5.6: Commit**

```bash
git add backend/src/main/java/com/edgeai/industrial/service/ \
        backend/src/test/java/com/edgeai/industrial/service/
git commit -m "feat(backend): add DeviceService and SensorService"
```

---

### Task 6: MQTT — Config e Subscriber

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/mqtt/MqttConfig.java`
- Create: `backend/src/main/java/com/edgeai/industrial/mqtt/MqttSubscriber.java`

- [ ] **Step 6.1: Criar MqttConfig.java**

Crie `backend/src/main/java/com/edgeai/industrial/mqtt/MqttConfig.java`:

```java
package com.edgeai.industrial.mqtt;

import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.integration.channel.DirectChannel;
import org.springframework.integration.mqtt.core.DefaultMqttPahoClientFactory;
import org.springframework.integration.mqtt.core.MqttPahoClientFactory;
import org.springframework.integration.mqtt.inbound.MqttPahoMessageDrivenChannelAdapter;
import org.springframework.integration.mqtt.support.DefaultPahoMessageConverter;
import org.springframework.messaging.MessageChannel;

@Configuration
public class MqttConfig {

    @Value("${mqtt.broker-url}")
    private String brokerUrl;

    @Value("${mqtt.client-id}")
    private String clientId;

    @Bean
    public MqttPahoClientFactory mqttClientFactory() {
        DefaultMqttPahoClientFactory factory = new DefaultMqttPahoClientFactory();
        MqttConnectOptions options = new MqttConnectOptions();
        options.setServerURIs(new String[]{brokerUrl});
        options.setCleanSession(true);
        options.setConnectionTimeout(10);
        options.setKeepAliveInterval(30);
        options.setAutomaticReconnect(true);
        factory.setConnectionOptions(options);
        return factory;
    }

    @Bean
    public MessageChannel mqttInputChannel() {
        return new DirectChannel();
    }

    @Bean
    public MqttPahoMessageDrivenChannelAdapter mqttInboundAdapter() {
        MqttPahoMessageDrivenChannelAdapter adapter =
                new MqttPahoMessageDrivenChannelAdapter(
                        clientId + "-sub",
                        mqttClientFactory(),
                        "sensor/data/#",
                        "device/status/#"
                );
        adapter.setConverter(new DefaultPahoMessageConverter());
        adapter.setOutputChannel(mqttInputChannel());
        adapter.setQos(1);
        return adapter;
    }
}
```

- [ ] **Step 6.2: Criar MqttSubscriber.java**

Crie `backend/src/main/java/com/edgeai/industrial/mqtt/MqttSubscriber.java`:

```java
package com.edgeai.industrial.mqtt;

import com.edgeai.industrial.dto.DeviceStatusDto;
import com.edgeai.industrial.dto.SensorPayloadDto;
import com.edgeai.industrial.domain.Device;
import com.edgeai.industrial.service.DeviceService;
import com.edgeai.industrial.service.SensorService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.integration.mqtt.support.MqttHeaders;
import org.springframework.messaging.Message;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class MqttSubscriber {

    private final ObjectMapper objectMapper;
    private final DeviceService deviceService;
    private final SensorService sensorService;

    @ServiceActivator(inputChannel = "mqttInputChannel")
    public void handleMessage(Message<?> message) {
        String topic = (String) message.getHeaders().get(MqttHeaders.RECEIVED_TOPIC);
        String payload = (String) message.getPayload();

        try {
            if (topic != null && topic.startsWith("sensor/data/")) {
                handleSensorData(payload);
            } else if (topic != null && topic.startsWith("device/status/")) {
                handleDeviceStatus(payload);
            }
        } catch (Exception e) {
            log.error("Error processing MQTT message on topic {}: {}", topic, e.getMessage());
        }
    }

    private void handleSensorData(String payload) throws Exception {
        SensorPayloadDto dto = objectMapper.readValue(payload, SensorPayloadDto.class);
        String firmwareVersion = dto.getInference() != null ? dto.getInference().getModelVersion() : "unknown";
        Device device = deviceService.findOrCreate(dto.getDeviceId(), firmwareVersion);
        deviceService.markOnline(device);
        sensorService.saveSensorPayload(device, dto);
        log.info("Saved sensor data from device {} — classification: {}",
                dto.getDeviceId(), dto.getInference().getClassification());
    }

    private void handleDeviceStatus(String payload) throws Exception {
        DeviceStatusDto dto = objectMapper.readValue(payload, DeviceStatusDto.class);
        Device device = deviceService.findOrCreate(dto.getDeviceId(), dto.getFirmwareVersion());
        if ("offline".equals(dto.getStatus())) {
            deviceService.markOffline(dto.getDeviceId());
        } else {
            deviceService.markOnline(device);
        }
        log.info("Device {} status: {}", dto.getDeviceId(), dto.getStatus());
    }
}
```

- [ ] **Step 6.3: Adicionar ObjectMapper bean na BackendApplication ou em um @Configuration**

Adicione em `backend/src/main/java/com/edgeai/industrial/BackendApplication.java`:

```java
package com.edgeai.industrial;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class BackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(BackendApplication.class, args);
    }

    @Bean
    public ObjectMapper objectMapper() {
        return new ObjectMapper().registerModule(new JavaTimeModule());
    }
}
```

- [ ] **Step 6.4: Commit**

```bash
git add backend/src/main/java/com/edgeai/industrial/mqtt/ \
        backend/src/main/java/com/edgeai/industrial/BackendApplication.java
git commit -m "feat(backend): add MQTT config and subscriber"
```

---

### Task 7: REST Controllers + Security permissiva (Fase 1)

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/controller/DeviceController.java`
- Create: `backend/src/main/java/com/edgeai/industrial/controller/SensorController.java`
- Create: `backend/src/main/java/com/edgeai/industrial/config/SecurityConfig.java`
- Create: `backend/src/test/java/com/edgeai/industrial/controller/SensorControllerTest.java`

- [ ] **Step 7.1: Criar SecurityConfig.java (Fase 1 — permite tudo)**

Crie `backend/src/main/java/com/edgeai/industrial/config/SecurityConfig.java`:

```java
package com.edgeai.industrial.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
                .csrf(AbstractHttpConfigurer::disable)
                .authorizeHttpRequests(a -> a.anyRequest().permitAll())
                .build();
    }
}
```

- [ ] **Step 7.2: Escrever teste do SensorController**

Crie `backend/src/test/java/com/edgeai/industrial/controller/SensorControllerTest.java`:

```java
package com.edgeai.industrial.controller;

import com.edgeai.industrial.dto.SensorReadingDto;
import com.edgeai.industrial.service.SensorService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(SensorController.class)
class SensorControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private SensorService sensorService;

    @Test
    void getAnomaliesReturns200() throws Exception {
        SensorReadingDto reading = new SensorReadingDto(
                OffsetDateTime.now(), UUID.randomUUID(), "esp32-sim-001",
                "temperature", 78.5, "C", "anomaly", 0.92
        );
        when(sensorService.getAnomalies()).thenReturn(List.of(reading));

        mockMvc.perform(get("/api/sensors/anomalies"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].sensorType").value("temperature"))
                .andExpect(jsonPath("$[0].classification").value("anomaly"));
    }

    @Test
    void getLatestReturns200() throws Exception {
        when(sensorService.getLatestPerDevice()).thenReturn(List.of());

        mockMvc.perform(get("/api/sensors/latest"))
                .andExpect(status().isOk());
    }
}
```

- [ ] **Step 7.3: Rodar o teste — deve falhar**

```bash
./gradlew test --tests "com.edgeai.industrial.controller.SensorControllerTest"
```

Esperado: `FAILED` — classe não existe

- [ ] **Step 7.4: Criar DeviceController.java**

Crie `backend/src/main/java/com/edgeai/industrial/controller/DeviceController.java`:

```java
package com.edgeai.industrial.controller;

import com.edgeai.industrial.domain.Device;
import com.edgeai.industrial.service.DeviceService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/devices")
@CrossOrigin(origins = "*")
@RequiredArgsConstructor
public class DeviceController {

    private final DeviceService deviceService;

    @GetMapping
    public ResponseEntity<List<Device>> listDevices() {
        return ResponseEntity.ok(deviceService.listAll());
    }
}
```

- [ ] **Step 7.5: Criar SensorController.java**

Crie `backend/src/main/java/com/edgeai/industrial/controller/SensorController.java`:

```java
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

    @GetMapping("/anomalies")
    public ResponseEntity<List<SensorReadingDto>> getAnomalies() {
        return ResponseEntity.ok(sensorService.getAnomalies());
    }
}
```

- [ ] **Step 7.6: Rodar os testes — devem passar**

```bash
./gradlew test --tests "com.edgeai.industrial.controller.SensorControllerTest"
```

Esperado: `PASSED`

- [ ] **Step 7.7: Commit**

```bash
git add backend/src/main/java/com/edgeai/industrial/controller/ \
        backend/src/main/java/com/edgeai/industrial/config/ \
        backend/src/test/java/com/edgeai/industrial/controller/
git commit -m "feat(backend): add REST controllers and permissive security (Phase 1)"
```

---

### Task 8: Smoke test do backend com simulador

**Files:** None (teste manual)

- [ ] **Step 8.1: Subir o backend**

```bash
cd backend
./gradlew bootRun
```

Aguardar log: `Started BackendApplication` e `MQTT connected`

- [ ] **Step 8.2: Rodar o simulador Python**

Em outro terminal:

```bash
cd "C:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
python firmware/simulator/esp32_sensor_simulator.py --interval 3 --anomaly-chance 0.3
```

Esperado no log do Spring Boot: `Saved sensor data from device esp32-sim-001 — classification: normal`

- [ ] **Step 8.3: Verificar dados no banco**

```bash
docker compose exec postgres psql -U edgeai -d edgeai \
  -c "SELECT time, sensor_type, value, classification FROM sensor_data ORDER BY time DESC LIMIT 9;"
```

Esperado: 9 linhas (3 sensores × 3 ciclos), com `classification` como `normal` ou `anomaly`.

- [ ] **Step 8.4: Verificar API REST**

```bash
curl http://localhost:8080/api/devices | python -m json.tool
curl http://localhost:8080/api/sensors/latest | python -m json.tool
curl http://localhost:8080/api/sensors/anomalies | python -m json.tool
```

Esperado: JSON com dados dos dispositivos e leituras.

- [ ] **Step 8.5: Commit de checkpoint**

```bash
git add .
git commit -m "chore: Phase 1 backend smoke test passed — MQTT→DB→REST working"
```

---

### Task 9: Frontend — Setup e configurações

**Files:**
- Create: `frontend/next.config.js`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/services/apiClient.ts`
- Create: `frontend/src/hooks/usePolling.ts`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx`

- [ ] **Step 9.1: Criar next.config.js**

Crie `frontend/next.config.js`:

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8080/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
```

- [ ] **Step 9.2: Criar tailwind.config.js**

Crie `frontend/tailwind.config.js`:

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

- [ ] **Step 9.3: Criar postcss.config.js**

Crie `frontend/postcss.config.js`:

```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 9.4: Criar tipos TypeScript**

Crie `frontend/src/types/index.ts`:

```ts
export interface Device {
  id: string;
  name: string;
  deviceType: string;
  firmwareVersion: string | null;
  location: string | null;
  status: string;
  lastSeenAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface SensorReading {
  time: string;
  deviceId: string;
  deviceName: string;
  sensorType: 'temperature' | 'vibration' | 'current';
  value: number;
  unit: string;
  classification: 'normal' | 'anomaly';
  anomalyScore: number;
}

export interface AnomalyRecord extends SensorReading {
  classification: 'anomaly';
}
```

- [ ] **Step 9.5: Criar ApiClient**

Crie `frontend/src/services/apiClient.ts`:

```ts
const BASE_URL = '/api';

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('jwt_token');
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const apiClient = {
  getDevices: () => request<import('@/types').Device[]>('/devices'),
  getLatestReadings: () => request<import('@/types').SensorReading[]>('/sensors/latest'),
  getReadings: (deviceId: string, from: string, to: string) =>
    request<import('@/types').SensorReading[]>(
      `/sensors/readings?deviceId=${deviceId}&from=${from}&to=${to}`
    ),
  getAnomalies: () => request<import('@/types').SensorReading[]>('/sensors/anomalies'),
  login: (email: string, password: string) =>
    request<{ token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
};
```

- [ ] **Step 9.6: Criar hook usePolling**

Crie `frontend/src/hooks/usePolling.ts`:

```ts
'use client';

import { useEffect, useRef } from 'react';

export function usePolling(callback: () => void, intervalMs: number) {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    callbackRef.current();
    const id = setInterval(() => callbackRef.current(), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
}
```

- [ ] **Step 9.7: Criar layout.tsx**

Crie `frontend/src/app/layout.tsx`:

```tsx
import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Edge AI Industrial',
  description: 'Monitoramento industrial com inferência em edge',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="bg-gray-900 text-gray-100 min-h-screen">{children}</body>
    </html>
  );
}
```

- [ ] **Step 9.8: Criar globals.css**

Crie `frontend/src/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 9.9: Criar page.tsx raiz (redirect)**

Crie `frontend/src/app/page.tsx`:

```tsx
import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/dashboard');
}
```

- [ ] **Step 9.10: Instalar dependências e verificar build**

```bash
cd frontend
npm install
npm run build 2>&1 | tail -20
```

Esperado: build sem erros (pode ter warnings de tipos — ok por ora)

- [ ] **Step 9.11: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): setup Next.js config, types, apiClient, usePolling hook"
```

---

### Task 10: Frontend — Dashboard com cards e 1 gráfico básico

**Files:**
- Create: `frontend/src/components/DeviceCard.tsx`
- Create: `frontend/src/app/dashboard/layout.tsx`
- Create: `frontend/src/app/dashboard/page.tsx`
- Create: `frontend/src/app/dashboard/readings/page.tsx`

- [ ] **Step 10.1: Criar DeviceCard.tsx**

Crie `frontend/src/components/DeviceCard.tsx`:

```tsx
'use client';

import { Device } from '@/types';

interface Props {
  device: Device;
}

export function DeviceCard({ device }: Props) {
  const isOnline = device.status === 'online';
  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-mono text-sm font-semibold text-white">{device.name}</h3>
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            isOnline ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
          }`}
        >
          {isOnline ? 'online' : 'offline'}
        </span>
      </div>
      <p className="text-gray-400 text-xs">Tipo: {device.deviceType}</p>
      <p className="text-gray-400 text-xs">
        Firmware: {device.firmwareVersion ?? 'desconhecido'}
      </p>
      {device.lastSeenAt && (
        <p className="text-gray-500 text-xs mt-1">
          Última leitura: {new Date(device.lastSeenAt).toLocaleString('pt-BR')}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 10.2: Criar dashboard/layout.tsx com sidebar**

Crie `frontend/src/app/dashboard/layout.tsx`:

```tsx
import Link from 'next/link';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <nav className="w-48 bg-gray-800 border-r border-gray-700 p-4 flex flex-col gap-2">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-4">Edge AI</p>
        <Link href="/dashboard" className="text-sm text-gray-300 hover:text-white py-1">
          Dispositivos
        </Link>
        <Link href="/dashboard/readings" className="text-sm text-gray-300 hover:text-white py-1">
          Leituras
        </Link>
        <Link href="/dashboard/anomalies" className="text-sm text-gray-300 hover:text-white py-1">
          Anomalias
        </Link>
      </nav>
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
```

- [ ] **Step 10.3: Criar dashboard/page.tsx (cards de dispositivos)**

Crie `frontend/src/app/dashboard/page.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { Device } from '@/types';
import { apiClient } from '@/services/apiClient';
import { DeviceCard } from '@/components/DeviceCard';
import { usePolling } from '@/hooks/usePolling';

export default function DashboardPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [error, setError] = useState<string | null>(null);

  usePolling(() => {
    apiClient.getDevices()
      .then(setDevices)
      .catch(() => setError('Erro ao carregar dispositivos'));
  }, 10000);

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6 text-white">Dispositivos</h1>
      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
      {devices.length === 0 && !error && (
        <p className="text-gray-500 text-sm">Nenhum dispositivo detectado ainda.</p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {devices.map((device) => (
          <DeviceCard key={device.id} device={device} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 10.4: Criar dashboard/readings/page.tsx com gráfico Recharts**

Crie `frontend/src/app/dashboard/readings/page.tsx`:

```tsx
'use client';

import { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { SensorReading } from '@/types';
import { apiClient } from '@/services/apiClient';
import { usePolling } from '@/hooks/usePolling';

function formatTime(isoString: string) {
  return new Date(isoString).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function ReadingsPage() {
  const [readings, setReadings] = useState<SensorReading[]>([]);

  usePolling(() => {
    apiClient.getLatestReadings()
      .then(setReadings)
      .catch(console.error);
  }, 10000);

  // Recharts espera um array de objetos com cada série como chave
  const chartData = readings
    .filter((r) => r.sensorType === 'temperature')
    .slice(0, 50)
    .map((r) => ({
      time: formatTime(r.time),
      temperature: r.value,
    }));

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6 text-white">Leituras de Sensores</h1>
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <h2 className="text-sm text-gray-400 mb-4">Temperatura (°C) — últimas leituras</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="time" stroke="#9ca3af" tick={{ fontSize: 11 }} />
            <YAxis stroke="#9ca3af" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
              labelStyle={{ color: '#e5e7eb' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="temperature"
              stroke="#60a5fa"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

- [ ] **Step 10.5: Testar o frontend no browser**

```bash
cd frontend
npm run dev
```

Abrir `http://localhost:3000/dashboard`. Com o backend e simulador rodando, deve mostrar:
- Card do dispositivo `esp32-sim-001` com status `online`
- Na página `/dashboard/readings`: gráfico de temperatura atualizando a cada 10s

- [ ] **Step 10.6: Commit — fim da Fase 1**

```bash
git add frontend/src/
git commit -m "feat(frontend): Phase 1 complete — dashboard with device cards and temperature chart"
```

---

## FASE 2 — Kafka (18–31 mai)

> Objetivo: Inserir Kafka entre MQTT subscriber e SensorService. O resto do sistema não muda.

---

### Task 11: KafkaConfig e SensorProducer

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/kafka/KafkaConfig.java`
- Create: `backend/src/main/java/com/edgeai/industrial/kafka/SensorProducer.java`

- [ ] **Step 11.1: Criar KafkaConfig.java**

Crie `backend/src/main/java/com/edgeai/industrial/kafka/KafkaConfig.java`:

```java
package com.edgeai.industrial.kafka;

import com.edgeai.industrial.dto.SensorPayloadDto;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.config.TopicBuilder;
import org.springframework.kafka.core.*;
import org.springframework.kafka.support.serializer.JsonDeserializer;

import java.util.Map;

@Configuration
public class KafkaConfig {

    @Value("${spring.kafka.bootstrap-servers}")
    private String bootstrapServers;

    public static final String SENSOR_READINGS_TOPIC = "sensor-readings";

    @Bean
    public NewTopic sensorReadingsTopic() {
        return TopicBuilder.name(SENSOR_READINGS_TOPIC)
                .partitions(1)
                .replicas(1)
                .build();
    }

    @Bean
    public ConsumerFactory<String, SensorPayloadDto> sensorConsumerFactory() {
        JsonDeserializer<SensorPayloadDto> deserializer =
                new JsonDeserializer<>(SensorPayloadDto.class, false);
        deserializer.addTrustedPackages("com.edgeai.industrial.dto");

        return new DefaultKafkaConsumerFactory<>(
                Map.of(
                        "bootstrap.servers", bootstrapServers,
                        "group.id", "edge-ai-group",
                        "auto.offset.reset", "earliest"
                ),
                new StringDeserializer(),
                deserializer
        );
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, SensorPayloadDto> kafkaListenerContainerFactory(
            ConsumerFactory<String, SensorPayloadDto> consumerFactory) {
        ConcurrentKafkaListenerContainerFactory<String, SensorPayloadDto> factory =
                new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory);
        return factory;
    }
}
```

- [ ] **Step 11.2: Criar SensorProducer.java**

Crie `backend/src/main/java/com/edgeai/industrial/kafka/SensorProducer.java`:

```java
package com.edgeai.industrial.kafka;

import com.edgeai.industrial.dto.SensorPayloadDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class SensorProducer {

    private final KafkaTemplate<String, SensorPayloadDto> kafkaTemplate;

    public void send(SensorPayloadDto payload) {
        kafkaTemplate.send(KafkaConfig.SENSOR_READINGS_TOPIC, payload.getDeviceId(), payload)
                .whenComplete((result, ex) -> {
                    if (ex != null) {
                        log.error("Failed to send to Kafka: {}", ex.getMessage());
                    } else {
                        log.debug("Kafka sent: device={} offset={}",
                                payload.getDeviceId(),
                                result.getRecordMetadata().offset());
                    }
                });
    }
}
```

- [ ] **Step 11.3: Commit**

```bash
git add backend/src/main/java/com/edgeai/industrial/kafka/KafkaConfig.java \
        backend/src/main/java/com/edgeai/industrial/kafka/SensorProducer.java
git commit -m "feat(backend): add Kafka config and SensorProducer"
```

---

### Task 12: SensorConsumer e refatoração do MqttSubscriber

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/kafka/SensorConsumer.java`
- Modify: `backend/src/main/java/com/edgeai/industrial/mqtt/MqttSubscriber.java`

- [ ] **Step 12.1: Criar SensorConsumer.java**

Crie `backend/src/main/java/com/edgeai/industrial/kafka/SensorConsumer.java`:

```java
package com.edgeai.industrial.kafka;

import com.edgeai.industrial.domain.Device;
import com.edgeai.industrial.dto.SensorPayloadDto;
import com.edgeai.industrial.service.DeviceService;
import com.edgeai.industrial.service.SensorService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class SensorConsumer {

    private final DeviceService deviceService;
    private final SensorService sensorService;

    @KafkaListener(
            topics = KafkaConfig.SENSOR_READINGS_TOPIC,
            groupId = "edge-ai-group",
            containerFactory = "kafkaListenerContainerFactory"
    )
    public void consume(SensorPayloadDto payload) {
        try {
            String firmwareVersion = payload.getInference() != null
                    ? payload.getInference().getModelVersion() : "unknown";
            Device device = deviceService.findOrCreate(payload.getDeviceId(), firmwareVersion);
            deviceService.markOnline(device);
            sensorService.saveSensorPayload(device, payload);
            log.info("Kafka consumed: device={} classification={}",
                    payload.getDeviceId(), payload.getInference().getClassification());
        } catch (Exception e) {
            log.error("Error consuming Kafka message: {}", e.getMessage());
        }
    }
}
```

- [ ] **Step 12.2: Refatorar MqttSubscriber para usar SensorProducer (remover chamada direta a SensorService)**

Substitua o conteúdo de `backend/src/main/java/com/edgeai/industrial/mqtt/MqttSubscriber.java`:

```java
package com.edgeai.industrial.mqtt;

import com.edgeai.industrial.dto.DeviceStatusDto;
import com.edgeai.industrial.dto.SensorPayloadDto;
import com.edgeai.industrial.domain.Device;
import com.edgeai.industrial.kafka.SensorProducer;
import com.edgeai.industrial.service.DeviceService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.integration.mqtt.support.MqttHeaders;
import org.springframework.messaging.Message;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class MqttSubscriber {

    private final ObjectMapper objectMapper;
    private final DeviceService deviceService;
    private final SensorProducer sensorProducer;

    @ServiceActivator(inputChannel = "mqttInputChannel")
    public void handleMessage(Message<?> message) {
        String topic = (String) message.getHeaders().get(MqttHeaders.RECEIVED_TOPIC);
        String payload = (String) message.getPayload();

        try {
            if (topic != null && topic.startsWith("sensor/data/")) {
                handleSensorData(payload);
            } else if (topic != null && topic.startsWith("device/status/")) {
                handleDeviceStatus(payload);
            }
        } catch (Exception e) {
            log.error("Error processing MQTT message on topic {}: {}", topic, e.getMessage());
        }
    }

    private void handleSensorData(String payload) throws Exception {
        SensorPayloadDto dto = objectMapper.readValue(payload, SensorPayloadDto.class);
        log.info("MQTT received from device {} — forwarding to Kafka", dto.getDeviceId());
        sensorProducer.send(dto);
    }

    private void handleDeviceStatus(String payload) throws Exception {
        DeviceStatusDto dto = objectMapper.readValue(payload, DeviceStatusDto.class);
        Device device = deviceService.findOrCreate(dto.getDeviceId(), dto.getFirmwareVersion());
        if ("offline".equals(dto.getStatus())) {
            deviceService.markOffline(dto.getDeviceId());
        } else {
            deviceService.markOnline(device);
        }
        log.info("Device {} status: {}", dto.getDeviceId(), dto.getStatus());
    }
}
```

- [ ] **Step 12.3: Commit**

```bash
git add backend/src/main/java/com/edgeai/industrial/kafka/SensorConsumer.java \
        backend/src/main/java/com/edgeai/industrial/mqtt/MqttSubscriber.java
git commit -m "feat(backend): integrate Kafka — MQTT subscriber now produces, consumer persists"
```

---

### Task 13: Verificar fluxo Kafka ponta-a-ponta

**Files:** None (teste manual)

- [ ] **Step 13.1: Reiniciar o backend e o simulador**

```bash
# Terminal 1 — backend
cd backend
./gradlew bootRun

# Terminal 2 — simulador
python firmware/simulator/esp32_sensor_simulator.py --interval 3
```

- [ ] **Step 13.2: Verificar logs do backend**

Esperado no log do Spring Boot:
```
MQTT received from device esp32-sim-001 — forwarding to Kafka
Kafka consumed: device=esp32-sim-001 classification=normal
```

- [ ] **Step 13.3: Verificar tópico Kafka via console**

```bash
docker compose exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic sensor-readings \
  --from-beginning \
  --max-messages 3
```

Esperado: 3 mensagens JSON com os payloads de sensor.

- [ ] **Step 13.4: Verificar que os dados ainda chegam no banco**

```bash
docker compose exec postgres psql -U edgeai -d edgeai \
  -c "SELECT COUNT(*) FROM sensor_data;"
```

Esperado: contagem crescendo a cada ciclo do simulador.

- [ ] **Step 13.5: Commit de checkpoint**

```bash
git add .
git commit -m "chore: Phase 2 complete — Kafka integrated, MQTT→Kafka→DB→REST verified"
```

---

## FASE 3 — JWT + Frontend Completo (01–14 jun)

> Objetivo: Adicionar autenticação JWT, proteger todos os endpoints, e completar o dashboard com gráfico multi-série e tabela de anomalias.

---

### Task 14: Seed do usuário admin no banco

**Files:**
- Create: `database/migrations/V002__seed_admin_user.sql`

- [ ] **Step 14.1: Gerar hash BCrypt da senha admin**

No terminal, criar um script temporário para gerar o hash:

```bash
cd backend
cat > /tmp/GenHash.java << 'EOF'
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
public class GenHash {
    public static void main(String[] args) {
        System.out.println(new BCryptPasswordEncoder().encode("admin123"));
    }
}
EOF
```

Alternativamente, usar o REPL online ou este hash pré-computado para `admin123`:

`$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2uheWG/igi.`

> Nota: Este hash é do Laravel/conhecido publicamente para fins de exemplo. Para produção, gere um novo com `new BCryptPasswordEncoder().encode("suasenha")`.

- [ ] **Step 14.2: Criar migration V002**

Crie `database/migrations/V002__seed_admin_user.sql`:

```sql
INSERT INTO users (id, email, password_hash, name, role, active)
VALUES (
    gen_random_uuid(),
    'admin@edgeai.local',
    '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2uheWG/igi.',
    'Admin',
    'admin',
    true
)
ON CONFLICT (email) DO NOTHING;
```

- [ ] **Step 14.3: Aplicar a migration no banco**

```bash
docker compose exec postgres psql -U edgeai -d edgeai \
  -f /docker-entrypoint-initdb.d/V002__seed_admin_user.sql
```

Se o arquivo não estiver montado, copiar e executar:

```bash
docker compose cp database/migrations/V002__seed_admin_user.sql postgres:/tmp/V002.sql
docker compose exec postgres psql -U edgeai -d edgeai -f /tmp/V002.sql
```

- [ ] **Step 14.4: Verificar usuário criado**

```bash
docker compose exec postgres psql -U edgeai -d edgeai \
  -c "SELECT email, name, role FROM users;"
```

Esperado: linha com `admin@edgeai.local`

- [ ] **Step 14.5: Commit**

```bash
git add database/migrations/V002__seed_admin_user.sql
git commit -m "feat(db): add admin user seed migration"
```

---

### Task 15: JWT — JwtService, JwtFilter, UserDetailsServiceImpl, SecurityConfig real

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/security/JwtService.java`
- Create: `backend/src/main/java/com/edgeai/industrial/security/JwtFilter.java`
- Create: `backend/src/main/java/com/edgeai/industrial/security/UserDetailsServiceImpl.java`
- Modify: `backend/src/main/java/com/edgeai/industrial/config/SecurityConfig.java`
- Create: `backend/src/test/java/com/edgeai/industrial/security/JwtServiceTest.java`

- [ ] **Step 15.1: Escrever teste do JwtService**

Crie `backend/src/test/java/com/edgeai/industrial/security/JwtServiceTest.java`:

```java
package com.edgeai.industrial.security;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class JwtServiceTest {

    private final JwtService jwtService = new JwtService(
            "dGVzdC1zZWNyZXQta2V5LXRoYXQtaXMtbG9uZy1lbm91Z2gtZm9yLUhTMjU2",
            86400000L
    );

    @Test
    void generateAndValidateToken() {
        String token = jwtService.generateToken("admin@edgeai.local");
        assertThat(jwtService.isTokenValid(token)).isTrue();
        assertThat(jwtService.extractEmail(token)).isEqualTo("admin@edgeai.local");
    }

    @Test
    void expiredTokenIsInvalid() {
        JwtService shortLived = new JwtService(
                "dGVzdC1zZWNyZXQta2V5LXRoYXQtaXMtbG9uZy1lbm91Z2gtZm9yLUhTMjU2",
                -1L
        );
        String token = shortLived.generateToken("user@test.com");
        assertThat(shortLived.isTokenValid(token)).isFalse();
    }
}
```

- [ ] **Step 15.2: Rodar o teste — deve falhar**

```bash
./gradlew test --tests "com.edgeai.industrial.security.JwtServiceTest"
```

Esperado: `FAILED`

- [ ] **Step 15.3: Criar JwtService.java**

Crie `backend/src/main/java/com/edgeai/industrial/security/JwtService.java`:

```java
package com.edgeai.industrial.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.util.Base64;
import java.util.Date;

@Service
public class JwtService {

    private final SecretKey key;
    private final long expirationMs;

    public JwtService(
            @Value("${jwt.secret}") String secret,
            @Value("${jwt.expiration}") long expirationMs) {
        this.key = Keys.hmacShaKeyFor(Base64.getDecoder().decode(secret));
        this.expirationMs = expirationMs;
    }

    public String generateToken(String email) {
        return Jwts.builder()
                .subject(email)
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + expirationMs))
                .signWith(key)
                .compact();
    }

    public String extractEmail(String token) {
        return parseClaims(token).getSubject();
    }

    public boolean isTokenValid(String token) {
        try {
            Claims claims = parseClaims(token);
            return claims.getExpiration().after(new Date());
        } catch (JwtException | IllegalArgumentException e) {
            return false;
        }
    }

    private Claims parseClaims(String token) {
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}
```

- [ ] **Step 15.4: Rodar o teste — deve passar**

```bash
./gradlew test --tests "com.edgeai.industrial.security.JwtServiceTest"
```

Esperado: `PASSED`

> Nota: O teste usa uma string Base64 hardcoded. Para a aplicação real, o `jwt.secret` em `application.yml` é `change-this-in-production` (raw string) — precisa ser Base64. Atualize `application.yml`:

```yaml
jwt:
  secret: ${JWT_SECRET:Y2hhbmdlLXRoaXMtaW4tcHJvZHVjdGlvbi1rZXktMzI=}
  expiration: ${JWT_EXPIRATION:86400000}
```

(`Y2hhbmdlLXRoaXMtaW4tcHJvZHVjdGlvbi1rZXktMzI=` é Base64 de `change-this-in-production-key-32`)

- [ ] **Step 15.5: Criar UserDetailsServiceImpl.java**

Crie `backend/src/main/java/com/edgeai/industrial/security/UserDetailsServiceImpl.java`:

```java
package com.edgeai.industrial.security;

import com.edgeai.industrial.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class UserDetailsServiceImpl implements UserDetailsService {

    private final UserRepository userRepository;

    @Override
    public UserDetails loadUserByUsername(String email) throws UsernameNotFoundException {
        return userRepository.findByEmail(email)
                .map(user -> new org.springframework.security.core.userdetails.User(
                        user.getEmail(),
                        user.getPasswordHash(),
                        List.of(new SimpleGrantedAuthority("ROLE_" + user.getRole().toUpperCase()))
                ))
                .orElseThrow(() -> new UsernameNotFoundException("User not found: " + email));
    }
}
```

- [ ] **Step 15.6: Criar JwtFilter.java**

Crie `backend/src/main/java/com/edgeai/industrial/security/JwtFilter.java`:

```java
package com.edgeai.industrial.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

@Component
@RequiredArgsConstructor
public class JwtFilter extends OncePerRequestFilter {

    private final JwtService jwtService;
    private final UserDetailsServiceImpl userDetailsService;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain)
            throws ServletException, IOException {

        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            chain.doFilter(request, response);
            return;
        }

        String token = authHeader.substring(7);
        if (!jwtService.isTokenValid(token)) {
            chain.doFilter(request, response);
            return;
        }

        String email = jwtService.extractEmail(token);
        if (email != null && SecurityContextHolder.getContext().getAuthentication() == null) {
            UserDetails userDetails = userDetailsService.loadUserByUsername(email);
            UsernamePasswordAuthenticationToken auth =
                    new UsernamePasswordAuthenticationToken(userDetails, null, userDetails.getAuthorities());
            auth.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
            SecurityContextHolder.getContext().setAuthentication(auth);
        }

        chain.doFilter(request, response);
    }
}
```

- [ ] **Step 15.7: Substituir SecurityConfig.java pela versão com JWT**

Substitua `backend/src/main/java/com/edgeai/industrial/config/SecurityConfig.java`:

```java
package com.edgeai.industrial.config;

import com.edgeai.industrial.security.JwtFilter;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.AuthenticationProvider;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import com.edgeai.industrial.security.UserDetailsServiceImpl;

@Configuration
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtFilter jwtFilter;
    private final UserDetailsServiceImpl userDetailsService;

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(a -> a
                        .requestMatchers("/api/auth/**").permitAll()
                        .requestMatchers("/actuator/**").permitAll()
                        .anyRequest().authenticated()
                )
                .authenticationProvider(authenticationProvider())
                .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class)
                .build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public AuthenticationProvider authenticationProvider() {
        DaoAuthenticationProvider provider = new DaoAuthenticationProvider();
        provider.setUserDetailsService(userDetailsService);
        provider.setPasswordEncoder(passwordEncoder());
        return provider;
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }
}
```

- [ ] **Step 15.8: Commit**

```bash
git add backend/src/main/java/com/edgeai/industrial/security/ \
        backend/src/main/java/com/edgeai/industrial/config/SecurityConfig.java \
        backend/src/main/resources/application.yml \
        backend/src/test/java/com/edgeai/industrial/security/
git commit -m "feat(backend): add JWT security — JwtService, JwtFilter, UserDetailsService, SecurityConfig"
```

---

### Task 16: AuthController — POST /api/auth/login

**Files:**
- Create: `backend/src/main/java/com/edgeai/industrial/controller/AuthController.java`
- Create: `backend/src/test/java/com/edgeai/industrial/controller/AuthControllerTest.java`

- [ ] **Step 16.1: Escrever teste do AuthController**

Crie `backend/src/test/java/com/edgeai/industrial/controller/AuthControllerTest.java`:

```java
package com.edgeai.industrial.controller;

import com.edgeai.industrial.security.JwtService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(AuthController.class)
class AuthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private AuthenticationManager authenticationManager;

    @MockBean
    private JwtService jwtService;

    @MockBean
    private com.edgeai.industrial.security.UserDetailsServiceImpl userDetailsService;

    @Test
    void loginReturnsTokenOnValidCredentials() throws Exception {
        Authentication auth = mock(Authentication.class);
        when(auth.getName()).thenReturn("admin@edgeai.local");
        when(authenticationManager.authenticate(any())).thenReturn(auth);
        when(jwtService.generateToken("admin@edgeai.local")).thenReturn("mock-jwt-token");

        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(
                                Map.of("email", "admin@edgeai.local", "password", "admin123"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.token").value("mock-jwt-token"));
    }

    @Test
    void loginReturns401OnBadCredentials() throws Exception {
        when(authenticationManager.authenticate(any()))
                .thenThrow(new BadCredentialsException("Bad credentials"));

        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(
                                Map.of("email", "wrong@edgeai.local", "password", "wrong"))))
                .andExpect(status().isUnauthorized());
    }
}
```

- [ ] **Step 16.2: Rodar o teste — deve falhar**

```bash
./gradlew test --tests "com.edgeai.industrial.controller.AuthControllerTest"
```

Esperado: `FAILED`

- [ ] **Step 16.3: Criar AuthController.java**

Crie `backend/src/main/java/com/edgeai/industrial/controller/AuthController.java`:

```java
package com.edgeai.industrial.controller;

import com.edgeai.industrial.security.JwtService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
@CrossOrigin(origins = "*")
@RequiredArgsConstructor
public class AuthController {

    private final AuthenticationManager authenticationManager;
    private final JwtService jwtService;

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> body) {
        try {
            Authentication auth = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(
                            body.get("email"), body.get("password")
                    )
            );
            String token = jwtService.generateToken(auth.getName());
            return ResponseEntity.ok(Map.of("token", token));
        } catch (BadCredentialsException e) {
            return ResponseEntity.status(401).body(Map.of("error", "Credenciais inválidas"));
        }
    }
}
```

- [ ] **Step 16.4: Rodar os testes — devem passar**

```bash
./gradlew test --tests "com.edgeai.industrial.controller.AuthControllerTest"
```

Esperado: `PASSED`

- [ ] **Step 16.5: Rodar todos os testes backend**

```bash
./gradlew test 2>&1 | tail -30
```

Esperado: todos os testes passando.

- [ ] **Step 16.6: Commit**

```bash
git add backend/src/main/java/com/edgeai/industrial/controller/AuthController.java \
        backend/src/test/java/com/edgeai/industrial/controller/AuthControllerTest.java
git commit -m "feat(backend): add AuthController — POST /api/auth/login returns JWT"
```

---

### Task 17: Frontend — Login page e middleware de autenticação

**Files:**
- Create: `frontend/src/app/(auth)/login/page.tsx`
- Create: `frontend/middleware.ts`

- [ ] **Step 17.1: Criar página de login**

Crie `frontend/src/app/(auth)/login/page.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/services/apiClient';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('admin@edgeai.local');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { token } = await apiClient.login(email, password);
      localStorage.setItem('jwt_token', token);
      router.push('/dashboard');
    } catch {
      setError('Email ou senha incorretos');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="bg-gray-800 p-8 rounded-lg border border-gray-700 w-full max-w-sm">
        <h1 className="text-xl font-semibold text-white mb-6">Edge AI Industrial</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              required
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Senha</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              required
            />
          </div>
          {error && <p className="text-red-400 text-xs">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded px-4 py-2 text-sm font-medium"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 17.2: Criar middleware de proteção de rotas**

Crie `frontend/middleware.ts`:

```ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('jwt_token')?.value;
  const isLoginPage = request.nextUrl.pathname.startsWith('/login');

  if (!token && !isLoginPage) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*'],
};
```

> Nota: O middleware do Next.js usa cookies, mas o frontend usa `localStorage`. Para compatibilidade, atualize o `handleSubmit` da LoginPage para salvar o token também em cookie:

Adicione em `handleSubmit` após `localStorage.setItem`:

```tsx
document.cookie = `jwt_token=${token}; path=/; max-age=86400`;
```

- [ ] **Step 17.3: Commit**

```bash
git add frontend/src/app/\(auth\)/ frontend/middleware.ts
git commit -m "feat(frontend): add login page and route protection middleware"
```

---

### Task 18: Frontend — SensorChart com 3 séries e AnomalyTable

**Files:**
- Create: `frontend/src/components/SensorChart.tsx`
- Create: `frontend/src/components/AnomalyTable.tsx`
- Modify: `frontend/src/app/dashboard/readings/page.tsx`
- Create: `frontend/src/app/dashboard/anomalies/page.tsx`

- [ ] **Step 18.1: Criar SensorChart.tsx com 3 séries**

Crie `frontend/src/components/SensorChart.tsx`:

```tsx
'use client';

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { SensorReading } from '@/types';

interface ChartPoint {
  time: string;
  temperature?: number;
  vibration?: number;
  current?: number;
}

function buildChartData(readings: SensorReading[]): ChartPoint[] {
  const byTime: Record<string, ChartPoint> = {};

  for (const r of readings) {
    const time = new Date(r.time).toLocaleTimeString('pt-BR', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
    if (!byTime[time]) byTime[time] = { time };
    if (r.sensorType === 'temperature') byTime[time].temperature = r.value;
    if (r.sensorType === 'vibration') byTime[time].vibration = r.value;
    if (r.sensorType === 'current') byTime[time].current = r.value;
  }

  return Object.values(byTime).slice(-50);
}

interface Props {
  readings: SensorReading[];
}

export function SensorChart({ readings }: Props) {
  const data = buildChartData(readings);

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <h2 className="text-sm text-gray-400 mb-4">Sensores em tempo real</h2>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="time" stroke="#9ca3af" tick={{ fontSize: 10 }} />
          <YAxis stroke="#9ca3af" tick={{ fontSize: 10 }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', fontSize: 12 }}
            labelStyle={{ color: '#e5e7eb' }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="temperature" stroke="#60a5fa" dot={false} strokeWidth={2} name="Temp (°C)" />
          <Line type="monotone" dataKey="vibration" stroke="#34d399" dot={false} strokeWidth={2} name="Vibração (mm/s)" />
          <Line type="monotone" dataKey="current" stroke="#f59e0b" dot={false} strokeWidth={2} name="Corrente (A)" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 18.2: Criar AnomalyTable.tsx**

Crie `frontend/src/components/AnomalyTable.tsx`:

```tsx
'use client';

import { SensorReading } from '@/types';

interface Props {
  anomalies: SensorReading[];
}

export function AnomalyTable({ anomalies }: Props) {
  if (anomalies.length === 0) {
    return <p className="text-gray-500 text-sm">Nenhuma anomalia detectada.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="border-b border-gray-700">
            <th className="py-2 pr-4 text-gray-400 font-medium">Timestamp</th>
            <th className="py-2 pr-4 text-gray-400 font-medium">Dispositivo</th>
            <th className="py-2 pr-4 text-gray-400 font-medium">Sensor</th>
            <th className="py-2 pr-4 text-gray-400 font-medium">Valor</th>
            <th className="py-2 pr-4 text-gray-400 font-medium">Score</th>
          </tr>
        </thead>
        <tbody>
          {anomalies.map((a, i) => (
            <tr key={i} className="border-b border-gray-800 hover:bg-gray-800/50">
              <td className="py-2 pr-4 text-gray-300 font-mono text-xs">
                {new Date(a.time).toLocaleString('pt-BR')}
              </td>
              <td className="py-2 pr-4 text-gray-300">{a.deviceName}</td>
              <td className="py-2 pr-4 text-gray-300">{a.sensorType}</td>
              <td className="py-2 pr-4 text-gray-300">
                {a.value.toFixed(2)} {a.unit}
              </td>
              <td className="py-2 pr-4">
                <span className={`font-mono text-xs px-2 py-0.5 rounded ${
                  a.anomalyScore >= 0.8
                    ? 'bg-red-900 text-red-300'
                    : 'bg-yellow-900 text-yellow-300'
                }`}>
                  {(a.anomalyScore * 100).toFixed(0)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 18.3: Atualizar dashboard/readings/page.tsx com SensorChart completo**

Substitua `frontend/src/app/dashboard/readings/page.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { SensorReading } from '@/types';
import { apiClient } from '@/services/apiClient';
import { SensorChart } from '@/components/SensorChart';
import { usePolling } from '@/hooks/usePolling';

export default function ReadingsPage() {
  const [readings, setReadings] = useState<SensorReading[]>([]);

  usePolling(() => {
    apiClient.getLatestReadings()
      .then(setReadings)
      .catch(console.error);
  }, 10000);

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6 text-white">Leituras em Tempo Real</h1>
      <SensorChart readings={readings} />
      <p className="text-xs text-gray-500 mt-2">Atualiza a cada 10 segundos. {readings.length} leituras.</p>
    </div>
  );
}
```

- [ ] **Step 18.4: Criar dashboard/anomalies/page.tsx**

Crie `frontend/src/app/dashboard/anomalies/page.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { SensorReading } from '@/types';
import { apiClient } from '@/services/apiClient';
import { AnomalyTable } from '@/components/AnomalyTable';
import { usePolling } from '@/hooks/usePolling';

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState<SensorReading[]>([]);

  usePolling(() => {
    apiClient.getAnomalies()
      .then(setAnomalies)
      .catch(console.error);
  }, 10000);

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6 text-white">Anomalias Detectadas</h1>
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <AnomalyTable anomalies={anomalies} />
      </div>
      <p className="text-xs text-gray-500 mt-2">{anomalies.length} anomalias nas últimas leituras.</p>
    </div>
  );
}
```

- [ ] **Step 18.5: Verificar build do frontend**

```bash
cd frontend
npm run build 2>&1 | tail -20
```

Esperado: build sem erros.

- [ ] **Step 18.6: Testar fluxo completo no browser**

```bash
npm run dev
```

1. Abrir `http://localhost:3000/login`
2. Fazer login com `admin@edgeai.local` / `admin123`
3. Verificar redirect para `/dashboard` com cards de dispositivos
4. Navegar para `/dashboard/readings` — gráfico com 3 séries
5. Navegar para `/dashboard/anomalies` — tabela de anomalias (com simulador rodando e `--anomaly-chance 0.5`)

- [ ] **Step 18.7: Commit — fim da Fase 3**

```bash
git add frontend/src/components/ \
        frontend/src/app/dashboard/ \
        frontend/src/app/\(auth\)/
git commit -m "feat(frontend): Phase 3 complete — login, 3-series chart, anomaly table"
```

---

## FASE 4 — Buffer + Relatório (15–30 jun)

> Objetivo: Capturar evidências, corrigir bugs encontrados, escrever relatório técnico.

---

### Task 19: Capturar evidências para o relatório

**Files:** None (capturas manuais)

- [ ] **Step 19.1: Screenshot — infraestrutura**

```bash
docker compose ps
```

Capturar screenshot do terminal com todos os serviços `running`.

- [ ] **Step 19.2: Screenshot — fluxo Kafka**

Com simulador rodando, abrir dois terminais:
- Terminal A: `./gradlew bootRun` (mostrar logs: `MQTT received → Kafka consumed`)
- Terminal B: log do consumer Kafka

Capturar screenshot de ambos.

- [ ] **Step 19.3: Gravar vídeo do fluxo ponta-a-ponta**

1. Abrir o dashboard no browser
2. Abrir o terminal do simulador ao lado
3. Gravar 30s mostrando os dados chegando e o gráfico atualizando

- [ ] **Step 19.4: Screenshot — autenticação JWT**

1. Abrir DevTools (F12) → Network
2. Fazer login em `http://localhost:3000/login`
3. Capturar a requisição `POST /api/auth/login` mostrando o token JWT na resposta
4. Capturar uma requisição `GET /api/sensors/latest` mostrando o header `Authorization: Bearer ...`

- [ ] **Step 19.5: Screenshot — tabela de anomalias**

Com `--anomaly-chance 0.5` no simulador, aguardar algumas anomalias e capturar screenshot da tabela preenchida.

- [ ] **Step 19.6: Commit final**

```bash
git add .
git commit -m "chore: Phase 4 complete — evidences captured, system verified end-to-end"
```

---

## Rodar todos os testes backend

```bash
cd backend
./gradlew test 2>&1 | grep -E "tests|failures|errors|BUILD"
```

Esperado:
```
X tests completed, 0 failures, 0 errors
BUILD SUCCESSFUL
```

---

## Referência rápida de comandos

| Ação | Comando |
|------|---------|
| Subir infraestrutura | `docker compose up -d` |
| Backend | `cd backend && ./gradlew bootRun` |
| Simulador | `python firmware/simulator/esp32_sensor_simulator.py --interval 3 --anomaly-chance 0.3` |
| Frontend | `cd frontend && npm run dev` |
| Testes backend | `cd backend && ./gradlew test` |
| Logs Kafka | `docker compose exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic sensor-readings --from-beginning` |
| Banco | `docker compose exec postgres psql -U edgeai -d edgeai` |

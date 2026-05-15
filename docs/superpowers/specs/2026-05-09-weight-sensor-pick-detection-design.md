# Weight Sensor & Pick Detection — Design Spec

**Data:** 2026-05-09
**Projeto:** Edge AI Industrial — UNIVESP PI-5
**Escopo:** Adicionar sensor de peso ao fluxo existente para detectar retiradas de produtos de prateleiras industriais, classificar o produto retirado por inferência de edge AI, e exibir análise de demanda no dashboard.

---

## Objetivo

Monitorar a demanda de produtos em prateleiras industriais. Cada ESP32 é fixado em uma prateleira com produto fixo. Quando o peso cai acima de um threshold, o firmware classifica qual produto foi retirado (pelo peso unitário) e publica um evento de retirada via MQTT. O backend persiste os eventos e expõe endpoints de demanda agregada. O dashboard exibe um gráfico de barras por produto e uma tabela de eventos recentes.

Não há identificação de operador — o foco é análise de quais produtos são mais demandados e em quais horários.

---

## Arquitetura

```
ESP32 (Wokwi)
  HX711 simulado por potenciômetro (A6)
  Detecção de queda de peso > 50g → pick event
  Classificação por peso unitário (catálogo hardcoded)
      │  MQTT  sensor/data/{device_id}
      ▼
EMQX Broker :1883
      │  Spring Integration MQTT (já existente)
      ▼
Spring Boot :8082
  SensorPayloadDto ← pick_event (opcional)
  SensorService → sensor_data (weight) + pick_events
  PickController → /api/picks/*
      ▼
TimescaleDB
  sensor_data  (sensor_type='weight' — hypertable existente)
  pick_events  (nova hypertable)
      ▼
Next.js :3000
  /dashboard/picks
    DemandChart (BarChart 7 dias)
    PickEventTable (polling 10s, 24h)
```

---

## Componentes

### 1. Wokwi — Circuito

Adicionar ao `diagram.json`:
- `wokwi-potentiometer` id=`pot3`, label=`"Weight (kg)"`, pino `A6`
- Conexões: `pot3:VCC → esp:3V3`, `pot3:GND → esp:GND`, `pot3:SIG → esp:A6`

### 2. Firmware — `wokwi/sketch.ino`

**Constantes novas:**
```cpp
#define WEIGHT_PIN     A6
const float WEIGHT_MAX_KG   = 10.0f;
const float PICK_THRESHOLD  = 0.050f;  // 50g mínimo pra contar como retirada
```

**Catálogo de produtos (hardcoded):**
```cpp
struct Product { const char* name; float unit_kg; float tolerance_kg; };
const Product CATALOG[] = {
  { "Parafuso M8",  0.025f, 0.008f },
  { "Porca M8",     0.010f, 0.004f },
  { "Arruela M8",   0.005f, 0.002f },
  { "Parafuso M12", 0.060f, 0.015f },
};
const int CATALOG_SIZE = 4;
```

**Lógica de pick detection:**
1. Lê peso atual a cada ciclo
2. Se `prevWeight - currentWeight > PICK_THRESHOLD`: pick detectado
   a. `delta = prevWeight - currentWeight`
   b. Itera catálogo: encontra produto onde `abs(delta % unit_kg - 0) < tolerance`
   c. `quantity = max(1, round(delta / unit_kg))`
   d. `confidence = 1.0 - abs(delta - quantity*unit_kg) / unit_kg` (0.0–1.0)
3. Atualiza `prevWeight = currentWeight` **sempre** (pick ou não) — rastreia o peso estável mais recente

**Payload MQTT — campos adicionados:**

Campo `sensors.weight`:
```json
"weight": { "value": 4.75, "unit": "kg" }
```

Campo `pick_event` (apenas quando `detected == true`):
```json
"pick_event": {
  "detected": true,
  "product_name": "Parafuso M8",
  "quantity": 3,
  "weight_delta_kg": 0.075,
  "confidence": 0.92
}
```

Nas publicações normais (sem pick), o campo `pick_event` é omitido do JSON.

### 3. Backend — Spring Boot

**Migration V003** (`database/migrations/V003__pick_events.sql`):
```sql
CREATE TABLE pick_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    time            TIMESTAMPTZ NOT NULL,
    device_id       UUID NOT NULL REFERENCES devices(id),
    product_name    TEXT NOT NULL,
    quantity        INT NOT NULL,
    weight_delta_kg FLOAT NOT NULL,
    confidence      FLOAT NOT NULL
);
SELECT create_hypertable('pick_events', 'time');
```

**DTOs novos:**

`PickEventPayloadDto` (deserialização MQTT):
```java
public record PickEventPayloadDto(
    boolean detected,
    String productName,
    int quantity,
    double weightDeltaKg,
    double confidence
) {}
```

`PickEventDto` (resposta REST):
```java
public record PickEventDto(
    Instant time,
    String deviceId,
    String deviceName,
    String productName,
    int quantity,
    double weightDeltaKg,
    double confidence
) {}
```

`ProductDemandDto` (resposta REST):
```java
public record ProductDemandDto(
    String productName,
    long totalPicks,
    long totalQuantity,
    Instant lastPick
) {}
```

**`SensorPayloadDto`** — adicionar campo opcional:
```java
@JsonProperty("pick_event")
private PickEventPayloadDto pickEvent;

@JsonProperty("sensors")
// já existente — adiciona leitura de "weight" automaticamente
```

**`PickEventRepository`** (JdbcTemplate):
- `save(deviceId, PickEventPayloadDto)` — INSERT em `pick_events`
- `findRecent(hours, limit)` — SELECT com JOIN em devices, ORDER BY time DESC
- `findDemandAggregate(hours)` — SELECT product_name, COUNT(*), SUM(quantity), MAX(time) GROUP BY product_name

**`PickService`:**
- `savePickEvent(UUID deviceId, PickEventPayloadDto dto)`
- `getRecentPicks(int hours)` → `List<PickEventDto>`
- `getProductDemand(int hours)` → `List<ProductDemandDto>`

**`SensorService.saveSensorPayload()`** — após salvar sensor_data normalmente:
```java
if (payload.getPickEvent() != null && payload.getPickEvent().isDetected()) {
    pickService.savePickEvent(device.getId(), payload.getPickEvent());
}
```

**`PickController`** (`/api/picks`):

| Método | Rota | Query params | Retorno |
|--------|------|-------------|---------|
| GET | `/api/picks/recent` | `hours=24` | `List<PickEventDto>` |
| GET | `/api/picks/demand` | `hours=168` | `List<ProductDemandDto>` |

Ambos públicos (sem auth) — mesma política permissiva do SecurityConfig atual.

### 4. Frontend — Next.js

**Nova página:** `frontend/src/app/dashboard/picks/page.tsx`
- Polling 10s via `usePolling`
- Chama `apiClient.getRecentPicks(24)` e `apiClient.getProductDemand(168)`
- Renderiza `DemandChart` (topo) + `PickEventTable` (abaixo)

**`DemandChart`** (`frontend/src/components/DemandChart.tsx`):
- Recharts `BarChart` responsivo
- Dados: `List<ProductDemandDto>` — X=`productName`, Y=`totalPicks`
- Estilo dark consistente com `SensorChart`

**`PickEventTable`** (`frontend/src/components/PickEventTable.tsx`):
- Colunas: Horário · Dispositivo · Produto · Qtd · Peso retirado · Confiança
- Badge de confiança: verde ≥ 85%, amarelo < 85% — mesmo padrão de `AnomalyTable`

**`apiClient.ts`** — dois métodos novos:
```typescript
getRecentPicks: (hours = 24) =>
  request<PickEvent[]>(`/picks/recent?hours=${hours}`),
getProductDemand: (hours = 168) =>
  request<ProductDemand[]>(`/picks/demand?hours=${hours}`),
```

**Tipos novos em `frontend/src/types/index.ts`:**
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

**Sidebar** (`frontend/src/components/Sidebar.tsx` ou equivalente):
- Adicionar link "Retiradas" → `/dashboard/picks`

---

## Fluxo end-to-end

1. Usuário gira `pot3` para baixo no Wokwi (simula remoção de produto)
2. ESP32 detecta `prevWeight - weight > 0.050kg`
3. Classifica produto pelo delta, serializa `pick_event` no payload JSON
4. Publica em `sensor/data/wokwi-esp32-001` via MQTT
5. `MqttSubscriber` recebe, deserializa `SensorPayloadDto` (campo `pick_event` preenchido)
6. `SensorService` salva `sensor_data` (weight) + chama `PickService.savePickEvent()`
7. `pick_events` INSERT via JdbcTemplate
8. Frontend polling `/api/picks/recent` e `/api/picks/demand` a cada 10s
9. Dashboard atualiza tabela e gráfico automaticamente

---

## O que não muda

- Tabela `sensor_data` — `weight` é apenas mais um `sensor_type`
- Fluxo Kafka — `MqttSubscriber` → `SensorProducer` → `SensorConsumer` → `SensorService` (inalterado)
- Endpoints existentes `/api/sensors/*`, `/api/devices`, `/api/auth/*`
- Páginas `/dashboard`, `/dashboard/readings`, `/dashboard/anomalies`
- Circuito existente no Wokwi (DHT22, pot1, pot2, LEDs)

---

## Arquivos a criar/modificar

| Arquivo | Ação |
|---------|------|
| `wokwi/diagram.json` | Modificar — adicionar pot3 |
| `wokwi/sketch.ino` | Modificar — weight reading + pick detection |
| `database/migrations/V003__pick_events.sql` | Criar |
| `backend/.../dto/PickEventPayloadDto.java` | Criar |
| `backend/.../dto/PickEventDto.java` | Criar |
| `backend/.../dto/ProductDemandDto.java` | Criar |
| `backend/.../dto/SensorPayloadDto.java` | Modificar — campo pickEvent |
| `backend/.../repository/PickEventRepository.java` | Criar |
| `backend/.../service/PickService.java` | Criar |
| `backend/.../service/SensorService.java` | Modificar — chamar PickService |
| `backend/.../controller/PickController.java` | Criar |
| `frontend/src/types/index.ts` | Modificar — PickEvent, ProductDemand |
| `frontend/src/services/apiClient.ts` | Modificar — 2 métodos novos |
| `frontend/src/components/DemandChart.tsx` | Criar |
| `frontend/src/components/PickEventTable.tsx` | Criar |
| `frontend/src/app/dashboard/picks/page.tsx` | Criar |
| `frontend/src/components/Sidebar.tsx` (ou equivalente) | Modificar — link Retiradas |

# Edge + Network Action Plan (ESP32 Integrated)

Date: 2026-04-02
Branch: `feature/esp32-edge-network-sim-bootstrap`
Owner: Edge/Firmware

## 1. Current Snapshot (Repository Reality)

This plan is based on the current codebase state:

- `firmware/src/main.cpp` is still TODO-only (no sensor, no MQTT flow yet).
- `backend` has dependencies/config only (no ingest pipeline implemented yet).
- `database/migrations/V001__initial_schema.sql` has the base tables:
  - `devices`
  - `sensor_data` (Timescale hypertable)
  - `users`
  - `alerts`
- `docker-compose.yml` already provides local infra for:
  - PostgreSQL + TimescaleDB
  - EMQX (MQTT broker)
  - Kafka
  - Redis

Conclusion: we can start Edge + Network development immediately by using a software simulator for ESP32/sensors while backend ingest is built.

## 2. Scope for This Evolution

Edge/Network delivery target for this feature:

1. Define and stabilize the MQTT contract from edge to cloud.
2. Implement a simulator that behaves like an ESP32 publishing processed data.
3. Validate end-to-end transport in local infra (simulator -> EMQX -> backend ingest when available).
4. Unblock backend with clear database-driven requirements.

## 3. MQTT Contract (Source of Truth for Integration)

### 3.1 Topic `sensor/data/{device_id}`

```json
{
  "device_id": "esp32-sim-001",
  "timestamp": "2026-04-02T13:40:00Z",
  "sensors": {
    "temperature": { "value": 31.2, "unit": "C" },
    "vibration": { "value": 0.42, "unit": "mm_s" },
    "current": { "value": 3.1, "unit": "A" }
  },
  "inference": {
    "classification": "normal",
    "anomaly_score": 0.18,
    "model_version": "sim-v1"
  }
}
```

### 3.2 Topic `device/status/{device_id}`

```json
{
  "device_id": "esp32-sim-001",
  "status": "online",
  "firmware_version": "sim-0.1.0",
  "uptime_seconds": 120,
  "free_memory": 182000,
  "wifi_rssi": -55,
  "timestamp": "2026-04-02T13:40:00Z"
}
```

## 4. Execution Plan (4 Phases)

## Phase A - Edge Baseline (Day 1-2)

Deliverables:

- Stabilize the JSON contract above.
- Create synthetic reading strategy (normal + anomaly injection).
- Prepare topic naming and QoS policy:
  - `sensor/data/{device_id}` with QoS 1
  - `device/status/{device_id}` with QoS 1

Acceptance criteria:

- Contract version `v1` documented and shared with backend.
- Simulator can emit deterministic data using a seed.

## Phase B - No-Hardware Simulation (Day 2-3)

Deliverables:

- Run `firmware/simulator/esp32_sensor_simulator.py` as an ESP32 stand-in.
- Publish periodic sensor and status messages to EMQX.
- Support dry-run mode for payload validation without broker.

Acceptance criteria:

- Messages visible in EMQX topic subscriptions.
- Controlled anomaly events generated (for alert-path testing).

## Phase C - Integration with Backend Ingest (Day 3-5)

Deliverables:

- Connect simulator stream to backend MQTT consumer.
- Map messages to `devices`, `sensor_data`, and `alerts`.
- Validate writes in PostgreSQL/TimescaleDB.

Acceptance criteria:

- `devices.last_seen_at` updates with status events.
- `sensor_data` receives time-series rows for each metric.
- Alert record created when anomaly policy is triggered.

## Phase D - Hardening + Handover (Day 5+)

Deliverables:

- Add basic observability checklist (message rates, reconnect behavior).
- Define failure tests (broker restart, malformed payload, duplicate events).
- Prepare move from simulator to real ESP32 firmware implementation.

Acceptance criteria:

- Recovery behavior documented.
- Backend and edge teams aligned on retry/idempotency strategy.

## 5. How to Test Without ESP32/Sensor (Implemented Path)

This repository now contains `firmware/simulator/esp32_sensor_simulator.py`.

Test sequence:

1. Start infrastructure:
   - `docker-compose up -d postgres emqx`
2. Optional dependency install:
   - `pip install -r firmware/simulator/requirements.txt`
3. Validate payload generation only:
   - `python firmware/simulator/esp32_sensor_simulator.py --dry-run --max-messages 5`
4. Publish to MQTT broker:
   - `python firmware/simulator/esp32_sensor_simulator.py --broker-host localhost --device-id esp32-sim-001`
5. Validate broker reception:
   - EMQX dashboard at `http://localhost:18083`
6. When backend ingest exists, validate DB writes:
   - `SELECT * FROM devices ORDER BY created_at DESC;`
   - `SELECT * FROM sensor_data ORDER BY time DESC LIMIT 20;`
   - `SELECT * FROM alerts ORDER BY created_at DESC LIMIT 20;`

## 6. Backend Dependency (What Must Be Built to Activate This Plan)

Backend requirements are documented in:

- `docs/api/BACKEND_EDGE_INGESTION_REQUIREMENTS.md`

Minimum required for edge plan activation:

1. MQTT subscription for:
   - `sensor/data/+`
   - `device/status/+`
2. JSON validation and mapping to DB entities.
3. Persistence flow:
   - upsert/update `devices`
   - insert into `sensor_data`
   - optional insert into `alerts` by anomaly rules
4. Observability:
   - log parsing errors and rejected payloads
   - expose ingest health via actuator/metrics

## 7. Immediate Next Sprint Checklist

- [ ] Run simulator in dry-run and MQTT mode locally.
- [ ] Backend developer implements ingest pipeline using contract `v1`.
- [ ] Validate first end-to-end insertion in `sensor_data`.
- [ ] Validate first anomaly-triggered row in `alerts`.
- [ ] Freeze `v1` contract before real ESP32 coding starts.

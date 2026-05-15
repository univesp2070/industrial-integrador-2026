# Backend Requirements for Edge Ingestion (Database-Driven)

Date: 2026-04-02
Input schema: `database/migrations/V001__initial_schema.sql`

## 1. Why This Exists

Edge/Network simulation is ready to emit MQTT messages, but it only becomes useful when backend ingest persists those events according to the current schema.

This file defines exactly what backend must implement so edge delivery can trigger the full pipeline.

## 2. Database Reality (Current Schema)

Tables available now:

1. `devices`
2. `sensor_data` (Timescale hypertable on `time`)
3. `users`
4. `alerts`

Important implications:

- `sensor_data` stores one metric per row (`sensor_type`, `value`, `unit`), so one MQTT payload with 3 sensors should produce 3 rows.
- `alerts` depends on `device_id` and optional `acknowledged_by` (FK to `users`).
- `devices.last_seen_at` should be updated from status events and data events.

## 3. MQTT Ingest Requirements (Mandatory)

Backend must subscribe to:

- `sensor/data/+`
- `device/status/+`

For each `sensor/data/{device_id}` message:

1. Validate required fields:
   - `device_id`, `timestamp`, `sensors`, `inference.classification`, `inference.anomaly_score`
2. Ensure device exists:
   - create if missing (initial default `status='inactive'` then update)
3. Update `devices`:
   - `last_seen_at = timestamp`
   - `updated_at = now()`
4. Insert rows in `sensor_data`:
   - one row per metric present in `sensors`
   - map `classification` and `anomaly_score` into each inserted row
   - store full payload context in `metadata` JSONB

For each `device/status/{device_id}` message:

1. Validate fields:
   - `device_id`, `status`, `timestamp`
2. Upsert/update `devices`:
   - `status`
   - `firmware_version` (if present)
   - `last_seen_at`
   - `updated_at`

## 4. Alert Generation Rules (Minimum Viable)

Given schema `alerts(alert_type, severity, message, acknowledged, created_at, ...)`:

Required first rule:

- If `inference.anomaly_score >= threshold` (initial threshold 0.8), insert into `alerts`:
  - `alert_type = 'anomaly_detected'`
  - `severity = 'high'`
  - `message` with `device_id`, metric summary, and score
  - `acknowledged = false`

Dedup suggestion for MVP:

- Avoid duplicate alert spam by suppressing identical alerts per device for a short cooldown window (example: 5 min).

## 5. Suggested Backend Components

Package mapping aligned to current project layout:

- `mqtt/MqttMessageHandler.java`
  - subscription, parsing, validation, routing
- `service/DeviceService.java`
  - create/update device, heartbeat updates
- `service/SensorDataService.java`
  - transform payload into time-series rows
- `service/AlertService.java`
  - threshold evaluation + alert creation
- `repository/*Repository.java`
  - custom queries for latest reading and active alerts
- `model/*`
  - entities and DTOs mapped to schema

## 6. Required API Endpoints for Edge Validation

Minimum endpoints to validate ingest quickly:

1. `GET /api/devices`
2. `GET /api/sensors/latest/{deviceId}`
3. `GET /api/sensors/data?deviceId={id}&start={iso}&end={iso}`
4. `GET /api/alerts?acknowledged=false`

Without these endpoints, edge simulation works but validation is slow because it depends on manual SQL checks only.

## 7. Definition of Done (Backend for Edge Activation)

Backend is considered ready for edge integration when:

- MQTT messages from simulator are consumed without errors.
- At least 1 device row is created/updated by status events.
- Each sensor payload produces expected rows in `sensor_data`.
- Anomaly payload creates at least 1 alert row in `alerts`.
- Endpoints above expose inserted data correctly.

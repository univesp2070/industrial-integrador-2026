# ESP32 Simulator (No Hardware)

This simulator lets you test the Edge + Network flow without an ESP32 board or physical sensors.

## What It Publishes

- `sensor/data/{device_id}`
- `device/status/{device_id}`

Payload format follows:

- `docs/EDGE_NETWORK_ESP32_ACTION_PLAN.md`

## Quick Start

1. Start local broker and database:
   - `docker-compose up -d postgres emqx`

2. Install dependency:
   - `pip install -r firmware/simulator/requirements.txt`

3. Validate payloads only (no MQTT connection):
   - `python firmware/simulator/esp32_sensor_simulator.py --dry-run --max-messages 5`

4. Publish to EMQX:
   - `python firmware/simulator/esp32_sensor_simulator.py --broker-host localhost --device-id esp32-sim-001`

## Useful Flags

- `--interval 1.0` publish sensor data every second
- `--status-interval 15` publish status every 15 seconds
- `--anomaly-chance 0.3` increase anomaly events
- `--max-messages 20` stop after 20 sensor payloads
- `--seed 123` deterministic synthetic data

## Validation Targets

1. EMQX dashboard:
   - `http://localhost:18083`
2. Backend ingest (when implemented):
   - rows in `devices`, `sensor_data`, and `alerts`

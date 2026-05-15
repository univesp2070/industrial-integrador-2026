#!/usr/bin/env python3
"""
ESP32 + sensor simulator for the Edge AI Industrial project.

It emits two MQTT streams compatible with the integration contract:
- sensor/data/{device_id}
- device/status/{device_id}

Use --dry-run to validate payload format without requiring an MQTT broker.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover - runtime dependency check
    mqtt = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class SensorSnapshot:
    temperature: float
    vibration: float
    current: float
    classification: str
    anomaly_score: float


class SyntheticSensorEngine:
    def __init__(self, anomaly_chance: float, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._anomaly_chance = anomaly_chance

    def _baseline(self, step: int) -> tuple[float, float, float]:
        wave = math.sin(step / 10.0)
        temperature = 27.0 + (2.5 * wave) + self._rng.uniform(-0.3, 0.3)
        vibration = 0.35 + (0.08 * wave) + self._rng.uniform(-0.02, 0.02)
        current = 2.7 + (0.25 * wave) + self._rng.uniform(-0.05, 0.05)
        return temperature, vibration, current

    def next_snapshot(self, step: int) -> SensorSnapshot:
        temperature, vibration, current = self._baseline(step)
        injected_anomaly = False

        if self._rng.random() < self._anomaly_chance:
            temperature += self._rng.uniform(9.0, 16.0)
            vibration += self._rng.uniform(0.35, 0.75)
            current += self._rng.uniform(0.8, 1.4)
            injected_anomaly = True

        anomaly_components = [
            max(0.0, (temperature - 34.0) / 14.0),
            max(0.0, (vibration - 0.55) / 0.45),
            max(0.0, (current - 3.3) / 1.2),
        ]
        anomaly_score = min(1.0, (sum(anomaly_components) / len(anomaly_components)) + (0.35 if injected_anomaly else 0.0))
        classification = "anomaly" if anomaly_score >= 0.65 else "normal"

        return SensorSnapshot(
            temperature=round(temperature, 3),
            vibration=round(vibration, 3),
            current=round(current, 3),
            classification=classification,
            anomaly_score=round(anomaly_score, 3),
        )


class Esp32Simulator:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.sensor_engine = SyntheticSensorEngine(args.anomaly_chance, args.seed)
        self.started_at = time.monotonic()
        self.status_topic = f"device/status/{self.args.device_id}"
        self.sensor_topic = f"sensor/data/{self.args.device_id}"
        self.client: mqtt.Client | None = None

        if not self.args.dry_run:
            if mqtt is None:
                raise RuntimeError(
                    "Dependency missing: paho-mqtt. Install with "
                    "'pip install -r firmware/simulator/requirements.txt'."
                )
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"{self.args.device_id}-sim")
            if self.args.username:
                self.client.username_pw_set(self.args.username, self.args.password or None)

    def _uptime_seconds(self) -> int:
        return int(time.monotonic() - self.started_at)

    def _status_payload(self, status: str, rng: random.Random) -> dict[str, Any]:
        return {
            "device_id": self.args.device_id,
            "status": status,
            "firmware_version": self.args.firmware_version,
            "uptime_seconds": self._uptime_seconds(),
            "free_memory": rng.randint(120_000, 220_000),
            "wifi_rssi": rng.randint(-68, -42),
            "timestamp": utc_now_iso(),
        }

    def _sensor_payload(self, snapshot: SensorSnapshot) -> dict[str, Any]:
        return {
            "device_id": self.args.device_id,
            "timestamp": utc_now_iso(),
            "sensors": {
                "temperature": {"value": snapshot.temperature, "unit": "C"},
                "vibration": {"value": snapshot.vibration, "unit": "mm_s"},
                "current": {"value": snapshot.current, "unit": "A"},
            },
            "inference": {
                "classification": snapshot.classification,
                "anomaly_score": snapshot.anomaly_score,
                "model_version": self.args.model_version,
            },
        }

    def _publish(self, topic: str, payload: dict[str, Any], qos: int = 1) -> None:
        serialized = json.dumps(payload, separators=(",", ":"))
        if self.args.dry_run:
            print(f"[DRY-RUN] {topic} {serialized}")
            return

        assert self.client is not None
        info = self.client.publish(topic, payload=serialized, qos=qos, retain=False)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed for topic {topic} with rc={info.rc}")
        print(f"[MQTT] {topic} {serialized}")

    def connect(self) -> None:
        if self.args.dry_run:
            return

        assert self.client is not None
        will_payload = self._status_payload(status="offline", rng=random.Random(self.args.seed))
        self.client.will_set(self.status_topic, payload=json.dumps(will_payload), qos=1, retain=False)
        self.client.connect(self.args.broker_host, self.args.broker_port, keepalive=30)
        self.client.loop_start()

    def disconnect(self) -> None:
        if self.args.dry_run:
            return

        assert self.client is not None
        try:
            self._publish(
                self.status_topic,
                self._status_payload(status="offline", rng=random.Random(self.args.seed)),
            )
        finally:
            self.client.loop_stop()
            self.client.disconnect()

    def run(self) -> int:
        message_count = 0
        step = 0
        rng = random.Random(self.args.seed)
        next_status_at = time.monotonic() + self.args.status_interval

        self.connect()
        self._publish(self.status_topic, self._status_payload(status="online", rng=rng))

        try:
            while True:
                now = time.monotonic()
                if now >= next_status_at:
                    self._publish(self.status_topic, self._status_payload(status="online", rng=rng))
                    next_status_at = now + self.args.status_interval

                snapshot = self.sensor_engine.next_snapshot(step)
                sensor_payload = self._sensor_payload(snapshot)
                self._publish(self.sensor_topic, sensor_payload)

                step += 1
                message_count += 1

                if self.args.max_messages is not None and message_count >= self.args.max_messages:
                    break

                time.sleep(self.args.interval)
        except KeyboardInterrupt:
            print("Interrupted by user.")
        finally:
            self.disconnect()

        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ESP32 + sensor MQTT simulator")
    parser.add_argument("--broker-host", default="localhost", help="MQTT broker host")
    parser.add_argument("--broker-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", default="", help="MQTT username")
    parser.add_argument("--password", default="", help="MQTT password")
    parser.add_argument("--device-id", default="esp32-sim-001", help="Device identifier")
    parser.add_argument("--interval", type=float, default=2.0, help="Sensor publish interval in seconds")
    parser.add_argument("--status-interval", type=float, default=30.0, help="Status publish interval in seconds")
    parser.add_argument("--anomaly-chance", type=float, default=0.15, help="Probability [0..1] of anomaly injection")
    parser.add_argument("--model-version", default="sim-v1", help="Inference model version label")
    parser.add_argument("--firmware-version", default="sim-0.1.0", help="Firmware version label")
    parser.add_argument("--max-messages", type=int, default=None, help="Stop after N sensor messages")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without MQTT connection")

    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be > 0")
    if args.status_interval <= 0:
        parser.error("--status-interval must be > 0")
    if args.anomaly_chance < 0 or args.anomaly_chance > 1:
        parser.error("--anomaly-chance must be between 0 and 1")

    return args


def main() -> int:
    args = parse_args()
    simulator = Esp32Simulator(args)
    return simulator.run()


if __name__ == "__main__":
    sys.exit(main())

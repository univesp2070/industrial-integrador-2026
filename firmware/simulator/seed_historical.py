#!/usr/bin/env python3
"""
Seed histórico para demonstração — insere 2 dias de leituras no banco.

Gera dados a cada 30s para 2 dispositivos simulados, com padrões realistas:
- Temperatura sobe no turno da manhã, cai à noite
- Anomalias distribuídas (~10% das leituras, clusters em alguns horários)
- Um "evento crítico" por dia simulando superaquecimento
"""

import math
import random
import uuid
from datetime import datetime, timezone, timedelta

try:
    import psycopg2
except ImportError:
    print("Instalando psycopg2-binary...")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"])
    import psycopg2

# ── Config ─────────────────────────────────────────────────────────────────
DB_HOST = "localhost"
DB_PORT = 5433
DB_NAME = "edgeai"
DB_USER = "edgeai"
DB_PASS = "edgeai"

INTERVAL_SECONDS = 30       # ponto de dado a cada 30s
DAYS_BACK = 2               # 2 dias de histórico
ANOMALY_BASE_CHANCE = 0.08  # 8% base de anomalia

DEVICES = [
    {
        "name": "ESP32-Linha-A",
        "device_type": "esp32-edge",
        "firmware_version": "1.2.0",
        "location": "Linha de Produção A",
    },
    {
        "name": "ESP32-Linha-B",
        "device_type": "esp32-edge",
        "firmware_version": "1.2.0",
        "location": "Linha de Produção B",
    },
]

# ── Geração de leitura ──────────────────────────────────────────────────────

def temperature_baseline(dt: datetime) -> float:
    """Temperatura sobe durante o turno (06h–18h), cai à noite."""
    hour = dt.hour + dt.minute / 60.0
    shift = math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 0.0
    return 24.0 + 6.0 * max(0.0, shift)

def is_critical_window(dt: datetime) -> bool:
    """Simula dois eventos críticos por dia: ~10h e ~16h (±15 min)."""
    hour = dt.hour + dt.minute / 60.0
    return abs(hour - 10.0) < 0.25 or abs(hour - 16.0) < 0.25

def make_snapshot(dt: datetime, rng: random.Random) -> dict:
    base_temp = temperature_baseline(dt)
    wave = math.sin(dt.timestamp() / 300.0)

    temp  = base_temp + 1.5 * wave + rng.uniform(-0.5, 0.5)
    vib   = 0.35 + 0.08 * wave + rng.uniform(-0.02, 0.02)
    curr  = 2.7  + 0.25 * wave + rng.uniform(-0.05, 0.05)

    anomaly_chance = ANOMALY_BASE_CHANCE
    if is_critical_window(dt):
        anomaly_chance = 0.6  # cluster de anomalias nos eventos críticos

    is_anomaly = rng.random() < anomaly_chance
    if is_anomaly:
        severity = rng.uniform(0.5, 1.0)
        temp  += rng.uniform(8.0, 18.0) * severity
        vib   += rng.uniform(0.3, 0.8)  * severity
        curr  += rng.uniform(0.8, 2.0)  * severity
        anomaly_score = rng.uniform(0.75, 0.99)
        classification = "anomaly"
    else:
        anomaly_score = rng.uniform(0.0, 0.25)
        classification = "normal"

    return {
        "temperature": round(temp, 2),
        "vibration":   round(vib, 4),
        "current":     round(curr, 3),
        "classification": classification,
        "anomaly_score":  round(anomaly_score, 4),
    }

# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print(f"Conectando ao banco {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    cur = conn.cursor()

    # Inserir ou recuperar dispositivos
    device_ids = []
    for d in DEVICES:
        cur.execute(
            """
            INSERT INTO devices (name, device_type, firmware_version, location, status, last_seen_at)
            VALUES (%s, %s, %s, %s, 'online', NOW())
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            (d["name"], d["device_type"], d["firmware_version"], d["location"]),
        )
        row = cur.fetchone()
        if row:
            device_ids.append(row[0])
        else:
            cur.execute("SELECT id FROM devices WHERE name = %s", (d["name"],))
            device_ids.append(cur.fetchone()[0])
        print(f"  Dispositivo: {d['name']} id={device_ids[-1]}")
    conn.commit()

    # Calcular range de tempo
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=DAYS_BACK)
    total_points = int(DAYS_BACK * 24 * 3600 / INTERVAL_SECONDS)
    sensors = [
        ("temperature", "C"),
        ("vibration",   "mm_s"),
        ("current",     "A"),
    ]

    print(f"\nInserindo {total_points * len(device_ids) * 3:,} leituras "
          f"({DAYS_BACK} dias × {len(device_ids)} dispositivos × 3 sensores)...")

    rng = random.Random(42)
    batch = []
    BATCH_SIZE = 1000
    inserted = 0

    for step in range(total_points):
        ts = start + timedelta(seconds=step * INTERVAL_SECONDS)
        for dev_id in device_ids:
            snap = make_snapshot(ts, rng)
            for sensor_type, unit in sensors:
                value = snap[sensor_type]
                batch.append((
                    ts, dev_id, sensor_type, value, unit,
                    snap["classification"], snap["anomaly_score"],
                ))

        if len(batch) >= BATCH_SIZE:
            cur.executemany(
                """
                INSERT INTO sensor_data (time, device_id, sensor_type, value, unit, classification, anomaly_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                batch,
            )
            conn.commit()
            inserted += len(batch)
            batch.clear()
            pct = step / total_points * 100
            print(f"  {pct:5.1f}% — {inserted:,} linhas inseridas", end="\r")

    if batch:
        cur.executemany(
            """
            INSERT INTO sensor_data (time, device_id, sensor_type, value, unit, classification, anomaly_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            batch,
        )
        conn.commit()
        inserted += len(batch)

    cur.execute("SELECT COUNT(*) FROM sensor_data")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sensor_data WHERE classification = 'anomaly'")
    anomalies = cur.fetchone()[0]

    print(f"\n\nSeed concluido!")
    print(f"  Total de leituras no banco : {total:,}")
    print(f"  Anomalias                  : {anomalies:,} ({anomalies/total*100:.1f}%)")
    print(f"  Período                    : {start.strftime('%Y-%m-%d %H:%M')} → agora")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
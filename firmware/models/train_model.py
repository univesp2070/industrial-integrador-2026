#!/usr/bin/env python3
"""
ML Training Pipeline — Edge AI Industrial
Trains an anomaly detection model from synthetic or real sensor data
and exports it to TFLite + model_data.h for the ESP32 firmware.

Usage:
    python train_model.py --synthetic
    python train_model.py --from-db --db-url postgresql://user:pass@localhost/edgeai
    python train_model.py --synthetic --from-db --db-url postgresql://... --quantize
    python train_model.py --synthetic --dry-run
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np


# ── Paths ────────────────────────────────────────────────────────────────────
_MODELS_DIR = Path(__file__).parent
_FIRMWARE_ROOT = _MODELS_DIR.parent
_TFLITE_PATH = _MODELS_DIR / "model.tflite"
_HEADER_PATH = _FIRMWARE_ROOT / "lib" / "inference" / "model_data.h"
_CPP_PATH = _FIRMWARE_ROOT / "lib" / "inference" / "model_data.cpp"


# ── DataLoader ────────────────────────────────────────────────────────────────
class DataLoader:
    """Generates or loads sensor training data as normalized numpy arrays.

    Features (X): [temperature/100, vibration/2, current/10]  shape (N, 3)
    Labels   (y): binary int  0=normal  1=anomaly              shape (N,)
    """

    # Anomaly score threshold used to binarize labels (matches simulator)
    LABEL_THRESHOLD = 0.65

    def __init__(
        self,
        samples: int = 10_000,
        anomaly_fraction: float = 0.2,
        seed: Optional[int] = 42,
        db_url: Optional[str] = None,
        device_id: str = "esp32-001",
    ) -> None:
        self.samples = samples
        self.anomaly_fraction = anomaly_fraction
        self.seed = seed
        self.db_url = db_url
        self.device_id = device_id
        self._rng = random.Random(seed)

    # ── Synthetic ─────────────────────────────────────────────────────────
    def _baseline(self, step: int) -> tuple[float, float, float]:
        wave = math.sin(step / 10.0)
        temp = 27.0 + 2.5 * wave + self._rng.uniform(-0.3, 0.3)
        vib  = 0.35 + 0.08 * wave + self._rng.uniform(-0.02, 0.02)
        curr = 2.7  + 0.25 * wave + self._rng.uniform(-0.05, 0.05)
        return temp, vib, curr

    def _anomaly_score(self, temp: float, vib: float, curr: float, injected: bool) -> float:
        components = [
            max(0.0, (temp - 34.0) / 14.0),
            max(0.0, (vib  - 0.55) / 0.45),
            max(0.0, (curr - 3.3)  / 1.2),
        ]
        score = sum(components) / len(components) + (0.35 if injected else 0.0)
        return min(1.0, score)

    def generate_synthetic(self) -> tuple[np.ndarray, np.ndarray]:
        """Returns (X_normalized, y_binary) from synthetic sensor data."""
        rows_X, rows_y = [], []
        for step in range(self.samples):
            temp, vib, curr = self._baseline(step)
            injected = self._rng.random() < self.anomaly_fraction
            if injected:
                temp += self._rng.uniform(9.0, 16.0)
                vib  += self._rng.uniform(0.35, 0.75)
                curr += self._rng.uniform(0.8, 1.4)
            score = self._anomaly_score(temp, vib, curr, injected)
            # Normalize — must match inference_engine.cpp USE_TFLITE path
            rows_X.append([temp / 100.0, vib / 2.0, curr / 10.0])
            rows_y.append(1 if score >= self.LABEL_THRESHOLD else 0)

        X = np.array(rows_X, dtype=np.float32)
        y = np.array(rows_y, dtype=np.int32)
        # Clamp to [0, 1] after normalization
        X = np.clip(X, 0.0, 1.0)
        return X, y

    # ── From DB ───────────────────────────────────────────────────────────
    def load_from_db(self) -> tuple[np.ndarray, np.ndarray]:
        """Returns (X_normalized, y_binary) from PostgreSQL sensor_data table."""
        try:
            import psycopg2
        except ImportError:
            raise RuntimeError("psycopg2-binary not installed. Run: pip install psycopg2-binary")

        if not self.db_url:
            raise ValueError("--db-url required for --from-db mode")

        query = """
            SELECT
                MAX(CASE WHEN sensor_type = 'temperature' THEN value END)       AS temperature,
                MAX(CASE WHEN sensor_type = 'vibration'   THEN value END)       AS vibration,
                MAX(CASE WHEN sensor_type = 'current'     THEN value END)       AS current,
                MAX(CASE WHEN sensor_type = 'temperature' THEN anomaly_score END) AS anomaly_score
            FROM sensor_data
            WHERE device_id = %(device_id)s
              AND time > NOW() - INTERVAL '7 days'
            GROUP BY date_trunc('second', time), device_id
            HAVING COUNT(DISTINCT sensor_type) = 3
            ORDER BY 1
        """
        conn = psycopg2.connect(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(query, {"device_id": self.device_id})
                rows = cur.fetchall()
        finally:
            conn.close()

        if not rows:
            raise RuntimeError(
                f"No data found for device_id='{self.device_id}' in the last 7 days."
            )

        data = np.array(rows, dtype=np.float32)
        X = np.column_stack([
            data[:, 0] / 100.0,  # temperature
            data[:, 1] / 2.0,    # vibration
            data[:, 2] / 10.0,   # current
        ])
        X = np.clip(X, 0.0, 1.0)
        y = (data[:, 3] >= self.LABEL_THRESHOLD).astype(np.int32)
        return X, y

    # ── Helpers ───────────────────────────────────────────────────────────
    def stats(self, X: np.ndarray, y: np.ndarray) -> dict:
        total = len(y)
        anomaly = int(y.sum())
        return {"total": total, "normal": total - anomaly, "anomaly": anomaly}


# ── ModelBuilder ──────────────────────────────────────────────────────────────
class ModelBuilder:
    """Builds and trains the Keras anomaly detection model."""

    def __init__(self, epochs: int = 20) -> None:
        self.epochs = epochs

    def build(self):
        """Returns compiled Keras model: Input(3) → Dense(8,relu) → Dense(4,relu) → Dense(1,sigmoid)."""
        import tensorflow as tf

        model = tf.keras.Sequential([
            tf.keras.layers.Dense(8, activation="relu", input_shape=(3,)),
            tf.keras.layers.Dense(4, activation="relu"),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ])
        model.compile(
            optimizer="adam",
            loss="binary_crossentropy",
            metrics=["accuracy", tf.keras.metrics.AUC(name="auc")],
        )
        return model

    def train(self, model, X: np.ndarray, y: np.ndarray) -> dict:
        """Trains model with 80/20 train/val split. Returns history dict."""
        from sklearn.model_selection import train_test_split

        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=self.epochs,
            batch_size=64,
            verbose=1,
        )
        return history.history


# ── TFLiteExporter ────────────────────────────────────────────────────────────
class TFLiteExporter:
    """Converts a trained Keras model to TFLite and saves the .tflite file."""

    def __init__(self, output_path: str | Path = _TFLITE_PATH, quantize: bool = False) -> None:
        self.output_path = Path(output_path)
        self.quantize = quantize

    def export(self, model, X_representative: np.ndarray) -> bytes:
        """Converts model to TFLite bytes, saves to output_path, returns bytes."""
        import tensorflow as tf

        converter = tf.lite.TFLiteConverter.from_keras_model(model)

        if self.quantize:
            converter.optimizations = [tf.lite.Optimize.DEFAULT]

            def representative_dataset():
                for i in range(min(200, len(X_representative))):
                    sample = X_representative[i:i+1].astype(np.float32)
                    yield [sample]

            converter.representative_dataset = representative_dataset
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
            converter.inference_input_type  = tf.int8
            converter.inference_output_type = tf.int8

        tflite_bytes = converter.convert()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_bytes(tflite_bytes)
        return tflite_bytes


# ── HeaderGenerator ───────────────────────────────────────────────────────────
class HeaderGenerator:
    """Writes g_model_data[] C array from .tflite bytes to model_data.h and model_data.cpp."""

    def __init__(
        self,
        header_path: str | Path = _HEADER_PATH,
        cpp_path: str | Path = _CPP_PATH,
    ) -> None:
        self.header_path = Path(header_path)
        self.cpp_path = Path(cpp_path)

    def generate(self, tflite_bytes: bytes, meta: dict) -> None:
        """Overwrites model_data.h and model_data.cpp with real model content."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        byte_hex = ", ".join(f"0x{b:02x}" for b in tflite_bytes)

        header_content = f"""\
#pragma once
// Auto-generated by firmware/models/train_model.py
// Date:         {now}
// Samples:      {meta.get('samples', '?')}
// Epochs:       {meta.get('epochs', '?')}
// Val accuracy: {meta.get('val_accuracy', '?'):.3f}
// Val AUC:      {meta.get('val_auc', '?'):.3f}
// Threshold (firmware): ANOMALY_THRESHOLD 0.8  (device_config.h)
// To regenerate: python firmware/models/train_model.py --synthetic

extern const unsigned char g_model_data[];
extern const int           g_model_data_len;
"""

        cpp_content = f"""\
#include "model_data.h"

// {len(tflite_bytes)} bytes — generated {now}
const unsigned char g_model_data[] = {{
    {byte_hex}
}};
const int g_model_data_len = {len(tflite_bytes)};
"""
        self.header_path.parent.mkdir(parents=True, exist_ok=True)
        self.header_path.write_text(header_content)
        self.cpp_path.write_text(cpp_content)


# ── CLI ───────────────────────────────────────────────────────────────────────
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train ESP32 anomaly detection model and export to TFLite."
    )
    parser.add_argument("--synthetic", action="store_true", help="Generate synthetic training data")
    parser.add_argument("--from-db",   action="store_true", help="Load data from PostgreSQL")
    parser.add_argument("--db-url",    default=None,        help="PostgreSQL connection URL")
    parser.add_argument("--device-id", default="esp32-001", help="Device ID to query from DB")
    parser.add_argument("--samples",   type=int, default=10_000, help="Synthetic samples (default 10000)")
    parser.add_argument("--epochs",    type=int, default=20,     help="Training epochs (default 20)")
    parser.add_argument("--quantize",  action="store_true", help="Apply INT8 quantization")
    parser.add_argument("--dry-run",   action="store_true", help="Print dataset stats without training")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if not args.synthetic and not getattr(args, "from_db", False):
        print("Error: specify --synthetic and/or --from-db", file=sys.stderr)
        sys.exit(1)

    loader = DataLoader(
        samples=args.samples,
        db_url=args.db_url,
        device_id=args.device_id,
    )

    X_parts, y_parts = [], []

    if args.synthetic:
        X_s, y_s = loader.generate_synthetic()
        stats = loader.stats(X_s, y_s)
        print(f"[data] Synthetic: {stats['total']} samples "
              f"({stats['normal']} normal, {stats['anomaly']} anomaly "
              f"— {stats['anomaly']/stats['total']:.1%})")
        X_parts.append(X_s)
        y_parts.append(y_s)

    if getattr(args, "from_db", False):
        X_d, y_d = loader.load_from_db()
        stats = loader.stats(X_d, y_d)
        print(f"[data] DB: {stats['total']} samples "
              f"({stats['normal']} normal, {stats['anomaly']} anomaly)")
        X_parts.append(X_d)
        y_parts.append(y_d)

    X = np.concatenate(X_parts)
    y = np.concatenate(y_parts)

    if args.dry_run:
        stats = loader.stats(X, y)
        print(f"[dry-run] Total: {stats['total']} | "
              f"Normal: {stats['normal']} | Anomaly: {stats['anomaly']}")
        print("[dry-run] Exiting without training.")
        return

    builder = ModelBuilder(epochs=args.epochs)
    model = builder.build()
    history = builder.train(model, X, y)

    last = lambda key: history[key][-1]
    print(f"[train] Epoch {args.epochs}/{args.epochs} — "
          f"loss: {last('loss'):.3f}  acc: {last('accuracy'):.3f}  "
          f"val_acc: {last('val_accuracy'):.3f}  val_auc: {last('auc'):.3f}")

    exporter = TFLiteExporter(output_path=_TFLITE_PATH, quantize=args.quantize)
    tflite_bytes = exporter.export(model, X)
    size_kb = len(tflite_bytes) / 1024
    print(f"[export] {_TFLITE_PATH} saved ({size_kb:.1f} KB)")

    meta = {
        "samples": len(X),
        "epochs": args.epochs,
        "val_accuracy": last("val_accuracy"),
        "val_auc": last("auc"),
    }
    gen = HeaderGenerator(header_path=_HEADER_PATH, cpp_path=_CPP_PATH)
    gen.generate(tflite_bytes, meta)
    print(f"[header] {_HEADER_PATH} updated")
    print(f"[header] {_CPP_PATH} updated")
    print("[done] Activate USE_TFLITE in platformio.ini [env:esp32] to use the model on ESP32")


if __name__ == "__main__":
    main()

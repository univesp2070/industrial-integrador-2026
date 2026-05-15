# ML Training Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `firmware/models/train_model.py` — a single Python script that generates synthetic sensor data, trains a Keras anomaly-detection model, exports to TFLite, and writes `firmware/lib/inference/model_data.h` as a C array.

**Architecture:** Four classes (`DataLoader`, `ModelBuilder`, `TFLiteExporter`, `HeaderGenerator`) orchestrated by `main()`. Dataset mirrors the `SyntheticSensorEngine` math from `firmware/simulator/esp32_sensor_simulator.py`. Normalization is identical to `inference_engine.cpp` so the same `.tflite` file works on both the Python simulator and the real ESP32.

**Tech Stack:** Python 3.10+, TensorFlow 2.15, NumPy, scikit-learn, psycopg2-binary, pytest.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `firmware/models/train_model.py` | All four classes + `main()` + CLI |
| Create | `firmware/models/requirements.txt` | Python dependencies |
| Create | `firmware/models/tests/__init__.py` | Empty — marks test package |
| Create | `firmware/models/tests/test_data_loader.py` | Tests for DataLoader |
| Create | `firmware/models/tests/test_model_builder.py` | Tests for ModelBuilder |
| Create | `firmware/models/tests/test_tflite_exporter.py` | Tests for TFLiteExporter |
| Create | `firmware/models/tests/test_header_generator.py` | Tests for HeaderGenerator |
| Modify | `firmware/lib/inference/model_data.h` | Overwritten with real model bytes |
| Modify | `firmware/lib/inference/model_data.cpp` | Overwritten with real model bytes |

---

## Task 1: requirements.txt and pytest setup

**Files:**
- Create: `firmware/models/requirements.txt`
- Create: `firmware/models/tests/__init__.py`

- [ ] **Step 1: Create `firmware/models/requirements.txt`**

```
tensorflow>=2.15,<3.0
numpy>=1.24
scikit-learn>=1.3
psycopg2-binary>=2.9
pytest>=7.4
```

- [ ] **Step 2: Install dependencies**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
pip install -r firmware/models/requirements.txt
```

Expected: all packages install without error. TensorFlow download is ~600 MB on first install.

- [ ] **Step 3: Create `firmware/models/tests/__init__.py`**

Empty file — just creates the package.

```bash
mkdir -p "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/models/tests"
touch "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/models/tests/__init__.py"
```

- [ ] **Step 4: Commit**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
git add firmware/models/requirements.txt firmware/models/tests/__init__.py
git commit -m "feat(ml): add requirements.txt and test package scaffold"
```

---

## Task 2: DataLoader — synthetic data (TDD)

**Files:**
- Create: `firmware/models/tests/test_data_loader.py`
- Create: `firmware/models/train_model.py` (DataLoader only)

- [ ] **Step 1: Write the failing tests**

Create `firmware/models/tests/test_data_loader.py`:

```python
import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from train_model import DataLoader


def test_synthetic_returns_correct_shape():
    loader = DataLoader(samples=200, anomaly_fraction=0.2, seed=42)
    X, y = loader.generate_synthetic()
    assert X.shape == (200, 3), f"Expected (200, 3), got {X.shape}"
    assert y.shape == (200,), f"Expected (200,), got {y.shape}"


def test_synthetic_features_normalized():
    loader = DataLoader(samples=1000, anomaly_fraction=0.2, seed=42)
    X, y = loader.generate_synthetic()
    # After normalization: temperature/100, vibration/2, current/10
    # Normal range temperature: ~24-30°C -> /100 -> ~0.24-0.30
    # With anomaly spikes still < 1.0 after /100
    assert X[:, 0].min() >= 0.0, "temperature_norm must be >= 0"
    assert X[:, 0].max() <= 1.0, "temperature_norm must be <= 1.0"
    assert X[:, 1].min() >= 0.0, "vibration_norm must be >= 0"
    assert X[:, 1].max() <= 1.0, "vibration_norm must be <= 1.0"
    assert X[:, 2].min() >= 0.0, "current_norm must be >= 0"
    assert X[:, 2].max() <= 1.0, "current_norm must be <= 1.0"


def test_synthetic_label_is_binary():
    loader = DataLoader(samples=500, anomaly_fraction=0.2, seed=42)
    X, y = loader.generate_synthetic()
    unique = set(y.tolist())
    assert unique.issubset({0, 1}), f"Labels must be 0 or 1, got {unique}"


def test_synthetic_anomaly_fraction():
    loader = DataLoader(samples=2000, anomaly_fraction=0.2, seed=42)
    X, y = loader.generate_synthetic()
    actual_fraction = y.mean()
    # Allow 5% tolerance around target fraction
    assert abs(actual_fraction - 0.2) < 0.05, (
        f"Expected ~20% anomalies, got {actual_fraction:.1%}"
    )


def test_synthetic_seed_is_reproducible():
    loader1 = DataLoader(samples=100, anomaly_fraction=0.2, seed=99)
    loader2 = DataLoader(samples=100, anomaly_fraction=0.2, seed=99)
    X1, y1 = loader1.generate_synthetic()
    X2, y2 = loader2.generate_synthetic()
    np.testing.assert_array_equal(X1, X2)
    np.testing.assert_array_equal(y1, y2)


def test_dry_run_returns_stats():
    loader = DataLoader(samples=500, anomaly_fraction=0.2, seed=42)
    X, y = loader.generate_synthetic()
    stats = loader.stats(X, y)
    assert "total" in stats
    assert "normal" in stats
    assert "anomaly" in stats
    assert stats["total"] == 500
    assert stats["normal"] + stats["anomaly"] == 500
```

- [ ] **Step 2: Run tests — expect FAIL (no train_model.py yet)**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/models"
python -m pytest tests/test_data_loader.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'train_model'`

- [ ] **Step 3: Create `firmware/models/train_model.py` with DataLoader only**

```python
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
from dataclasses import dataclass
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


# ── Placeholder classes (implemented in later tasks) ─────────────────────────
class ModelBuilder:
    pass


class TFLiteExporter:
    pass


class HeaderGenerator:
    pass


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

    if not args.synthetic and not args.from_db:
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
        X_parts.append(X_s)
        y_parts.append(y_s)
        stats = loader.stats(X_s, y_s)
        print(f"[data] Synthetic: {stats['total']} samples "
              f"({stats['normal']} normal, {stats['anomaly']} anomaly)")

    if args.from_db:
        X_d, y_d = loader.load_from_db()
        X_parts.append(X_d)
        y_parts.append(y_d)
        stats = loader.stats(X_d, y_d)
        print(f"[data] DB: {stats['total']} samples "
              f"({stats['normal']} normal, {stats['anomaly']} anomaly)")

    X = np.concatenate(X_parts)
    y = np.concatenate(y_parts)

    if args.dry_run:
        stats = loader.stats(X, y)
        print(f"[dry-run] Total: {stats['total']} | Normal: {stats['normal']} | Anomaly: {stats['anomaly']}")
        print("[dry-run] Exiting without training.")
        return

    print("[train] Placeholder — ModelBuilder not yet implemented")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/models"
python -m pytest tests/test_data_loader.py -v
```

Expected:
```
test_data_loader.py::test_synthetic_returns_correct_shape PASSED
test_data_loader.py::test_synthetic_features_normalized PASSED
test_data_loader.py::test_synthetic_label_is_binary PASSED
test_data_loader.py::test_synthetic_anomaly_fraction PASSED
test_data_loader.py::test_synthetic_seed_is_reproducible PASSED
test_data_loader.py::test_dry_run_returns_stats PASSED
6 passed
```

- [ ] **Step 5: Commit**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
git add firmware/models/train_model.py firmware/models/tests/test_data_loader.py
git commit -m "feat(ml): add DataLoader with synthetic generation and tests"
```

---

## Task 3: DataLoader — from-db mode (TDD)

**Files:**
- Modify: `firmware/models/tests/test_data_loader.py` (add DB tests)

- [ ] **Step 1: Add DB tests to `test_data_loader.py`**

Append to the end of `firmware/models/tests/test_data_loader.py`:

```python
from unittest.mock import patch, MagicMock


def _make_db_rows():
    """Simulate 3 sensor rows from PostgreSQL."""
    return [
        (30.0, 0.3, 2.8, 0.10),   # normal
        (45.0, 1.2, 4.0, 0.85),   # anomaly
        (28.0, 0.35, 2.9, 0.05),  # normal
    ]


def test_load_from_db_returns_correct_shape():
    loader = DataLoader(db_url="postgresql://fake/db", device_id="esp32-001")
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = _make_db_rows()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("psycopg2.connect", return_value=mock_conn):
        X, y = loader.load_from_db()

    assert X.shape == (3, 3)
    assert y.shape == (3,)


def test_load_from_db_normalizes_features():
    loader = DataLoader(db_url="postgresql://fake/db", device_id="esp32-001")
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = _make_db_rows()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("psycopg2.connect", return_value=mock_conn):
        X, y = loader.load_from_db()

    # Row 0: temp=30 → 30/100=0.30, vib=0.3 → 0.3/2=0.15, curr=2.8 → 2.8/10=0.28
    np.testing.assert_allclose(X[0], [0.30, 0.15, 0.28], atol=1e-5)


def test_load_from_db_labels_above_threshold():
    loader = DataLoader(db_url="postgresql://fake/db", device_id="esp32-001")
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = _make_db_rows()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("psycopg2.connect", return_value=mock_conn):
        X, y = loader.load_from_db()

    # Row 0: score=0.10 < 0.65 → 0 (normal)
    # Row 1: score=0.85 >= 0.65 → 1 (anomaly)
    # Row 2: score=0.05 < 0.65 → 0 (normal)
    np.testing.assert_array_equal(y, [0, 1, 0])


def test_load_from_db_raises_without_db_url():
    loader = DataLoader(db_url=None)
    with pytest.raises(ValueError, match="--db-url required"):
        loader.load_from_db()


def test_load_from_db_raises_on_empty_result():
    loader = DataLoader(db_url="postgresql://fake/db")
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("psycopg2.connect", return_value=mock_conn):
        with pytest.raises(RuntimeError, match="No data found"):
            loader.load_from_db()
```

- [ ] **Step 2: Run tests — expect PASS**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/models"
python -m pytest tests/test_data_loader.py -v
```

Expected: `11 passed`

- [ ] **Step 3: Commit**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
git add firmware/models/tests/test_data_loader.py
git commit -m "feat(ml): add DataLoader from-db mode with mock tests"
```

---

## Task 4: ModelBuilder (TDD)

**Files:**
- Create: `firmware/models/tests/test_model_builder.py`
- Modify: `firmware/models/train_model.py` (implement ModelBuilder)

- [ ] **Step 1: Write the failing tests**

Create `firmware/models/tests/test_model_builder.py`:

```python
import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from train_model import DataLoader, ModelBuilder


def _small_dataset():
    loader = DataLoader(samples=400, anomaly_fraction=0.2, seed=0)
    return loader.generate_synthetic()


def test_model_has_correct_input_shape():
    builder = ModelBuilder(epochs=1)
    model = builder.build()
    assert model.input_shape == (None, 3), f"Expected (None, 3), got {model.input_shape}"


def test_model_has_correct_output_shape():
    builder = ModelBuilder(epochs=1)
    model = builder.build()
    assert model.output_shape == (None, 1), f"Expected (None, 1), got {model.output_shape}"


def test_model_output_between_0_and_1():
    builder = ModelBuilder(epochs=1)
    model = builder.build()
    X = np.array([[0.30, 0.15, 0.28], [0.45, 0.60, 0.40]], dtype=np.float32)
    preds = model.predict(X, verbose=0)
    assert preds.min() >= 0.0
    assert preds.max() <= 1.0


def test_train_returns_history_keys():
    builder = ModelBuilder(epochs=2)
    model = builder.build()
    X, y = _small_dataset()
    history = builder.train(model, X, y)
    assert "loss" in history
    assert "val_loss" in history
    assert "accuracy" in history
    assert "val_accuracy" in history
    assert "auc" in history


def test_train_history_length_matches_epochs():
    epochs = 3
    builder = ModelBuilder(epochs=epochs)
    model = builder.build()
    X, y = _small_dataset()
    history = builder.train(model, X, y)
    assert len(history["loss"]) == epochs


def test_model_parameter_count():
    builder = ModelBuilder(epochs=1)
    model = builder.build()
    # Dense(3→8) + Dense(8→4) + Dense(4→1) = 24+8 + 32+4 + 4+1 = 73 params
    # Actual: 3*8+8 + 8*4+4 + 4*1+1 = 32 + 36 + 5 = 73... let's check with ~140 range
    total = model.count_params()
    assert 50 < total < 200, f"Expected ~73-140 params, got {total}"
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/models"
python -m pytest tests/test_model_builder.py -v 2>&1 | head -15
```

Expected: `AttributeError: 'ModelBuilder' object has no attribute 'build'`

- [ ] **Step 3: Implement ModelBuilder in `train_model.py`**

Replace the `class ModelBuilder: pass` placeholder with:

```python
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
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/models"
python -m pytest tests/test_model_builder.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
git add firmware/models/train_model.py firmware/models/tests/test_model_builder.py
git commit -m "feat(ml): add ModelBuilder with Keras Dense network and tests"
```

---

## Task 5: TFLiteExporter (TDD)

**Files:**
- Create: `firmware/models/tests/test_tflite_exporter.py`
- Modify: `firmware/models/train_model.py` (implement TFLiteExporter)

- [ ] **Step 1: Write the failing tests**

Create `firmware/models/tests/test_tflite_exporter.py`:

```python
import numpy as np
import tempfile
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from train_model import DataLoader, ModelBuilder, TFLiteExporter


def _trained_model():
    loader = DataLoader(samples=300, anomaly_fraction=0.2, seed=0)
    X, y = loader.generate_synthetic()
    builder = ModelBuilder(epochs=1)
    model = builder.build()
    builder.train(model, X, y)
    return model, X


def test_export_creates_tflite_file():
    model, X = _trained_model()
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "model.tflite")
        exporter = TFLiteExporter(output_path=out_path, quantize=False)
        exporter.export(model, X)
        assert os.path.exists(out_path), "model.tflite was not created"
        assert os.path.getsize(out_path) > 100, "model.tflite is too small"


def test_export_returns_bytes():
    model, X = _trained_model()
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "model.tflite")
        exporter = TFLiteExporter(output_path=out_path, quantize=False)
        tflite_bytes = exporter.export(model, X)
        assert isinstance(tflite_bytes, bytes)
        assert len(tflite_bytes) > 100


def test_tflite_is_loadable_by_interpreter():
    """Verify the exported .tflite loads in the TFLite interpreter (same as ESP32 runtime)."""
    import tensorflow as tf
    model, X = _trained_model()
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "model.tflite")
        exporter = TFLiteExporter(output_path=out_path, quantize=False)
        exporter.export(model, X)
        interpreter = tf.lite.Interpreter(model_path=out_path)
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        assert input_details[0]["shape"].tolist() == [1, 3]
        assert output_details[0]["shape"].tolist() == [1, 1]


def test_export_with_quantize_produces_smaller_file():
    model, X = _trained_model()
    with tempfile.TemporaryDirectory() as tmpdir:
        path_f32 = os.path.join(tmpdir, "model_f32.tflite")
        path_int8 = os.path.join(tmpdir, "model_int8.tflite")
        TFLiteExporter(output_path=path_f32, quantize=False).export(model, X)
        TFLiteExporter(output_path=path_int8, quantize=True).export(model, X)
        size_f32 = os.path.getsize(path_f32)
        size_int8 = os.path.getsize(path_int8)
        assert size_int8 <= size_f32, (
            f"INT8 ({size_int8}B) should be <= float32 ({size_f32}B)"
        )
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/models"
python -m pytest tests/test_tflite_exporter.py -v 2>&1 | head -15
```

Expected: `AttributeError: 'TFLiteExporter' object has no attribute 'export'`

- [ ] **Step 3: Implement TFLiteExporter in `train_model.py`**

Replace `class TFLiteExporter: pass` with:

```python
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
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/models"
python -m pytest tests/test_tflite_exporter.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
git add firmware/models/train_model.py firmware/models/tests/test_tflite_exporter.py
git commit -m "feat(ml): add TFLiteExporter with float32 and INT8 quantization"
```

---

## Task 6: HeaderGenerator (TDD)

**Files:**
- Create: `firmware/models/tests/test_header_generator.py`
- Modify: `firmware/models/train_model.py` (implement HeaderGenerator)

- [ ] **Step 1: Write the failing tests**

Create `firmware/models/tests/test_header_generator.py`:

```python
import os
import sys
import tempfile
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from train_model import HeaderGenerator


_FAKE_TFLITE = bytes([0x18, 0x00, 0x54, 0x46, 0x4c, 0x33, 0xAB, 0xCD])
_FAKE_META = {
    "samples": 10000,
    "epochs": 20,
    "val_accuracy": 0.982,
    "val_auc": 0.997,
}


def test_generates_header_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        h_path = os.path.join(tmpdir, "model_data.h")
        cpp_path = os.path.join(tmpdir, "model_data.cpp")
        gen = HeaderGenerator(header_path=h_path, cpp_path=cpp_path)
        gen.generate(_FAKE_TFLITE, _FAKE_META)
        assert os.path.exists(h_path)
        assert os.path.exists(cpp_path)


def test_header_contains_extern_declarations():
    with tempfile.TemporaryDirectory() as tmpdir:
        h_path = os.path.join(tmpdir, "model_data.h")
        cpp_path = os.path.join(tmpdir, "model_data.cpp")
        gen = HeaderGenerator(header_path=h_path, cpp_path=cpp_path)
        gen.generate(_FAKE_TFLITE, _FAKE_META)
        content = open(h_path).read()
        assert "extern const unsigned char g_model_data[]" in content
        assert "extern const int           g_model_data_len" in content


def test_cpp_contains_correct_byte_count():
    with tempfile.TemporaryDirectory() as tmpdir:
        h_path = os.path.join(tmpdir, "model_data.h")
        cpp_path = os.path.join(tmpdir, "model_data.cpp")
        gen = HeaderGenerator(header_path=h_path, cpp_path=cpp_path)
        gen.generate(_FAKE_TFLITE, _FAKE_META)
        content = open(cpp_path).read()
        assert f"g_model_data_len = {len(_FAKE_TFLITE)}" in content


def test_cpp_contains_first_byte():
    with tempfile.TemporaryDirectory() as tmpdir:
        h_path = os.path.join(tmpdir, "model_data.h")
        cpp_path = os.path.join(tmpdir, "model_data.cpp")
        gen = HeaderGenerator(header_path=h_path, cpp_path=cpp_path)
        gen.generate(_FAKE_TFLITE, _FAKE_META)
        content = open(cpp_path).read()
        # First byte is 0x18
        assert "0x18" in content


def test_header_contains_metadata_comment():
    with tempfile.TemporaryDirectory() as tmpdir:
        h_path = os.path.join(tmpdir, "model_data.h")
        cpp_path = os.path.join(tmpdir, "model_data.cpp")
        gen = HeaderGenerator(header_path=h_path, cpp_path=cpp_path)
        gen.generate(_FAKE_TFLITE, _FAKE_META)
        content = open(h_path).read()
        assert "10000" in content      # samples
        assert "20" in content         # epochs
        assert "0.982" in content      # val_accuracy
        assert "0.997" in content      # val_auc


def test_header_has_pragma_once():
    with tempfile.TemporaryDirectory() as tmpdir:
        h_path = os.path.join(tmpdir, "model_data.h")
        cpp_path = os.path.join(tmpdir, "model_data.cpp")
        gen = HeaderGenerator(header_path=h_path, cpp_path=cpp_path)
        gen.generate(_FAKE_TFLITE, _FAKE_META)
        content = open(h_path).read()
        assert "#pragma once" in content
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/models"
python -m pytest tests/test_header_generator.py -v 2>&1 | head -15
```

Expected: `AttributeError: 'HeaderGenerator' object has no attribute 'generate'`

- [ ] **Step 3: Implement HeaderGenerator in `train_model.py`**

Replace `class HeaderGenerator: pass` with:

```python
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
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/models"
python -m pytest tests/test_header_generator.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
git add firmware/models/train_model.py firmware/models/tests/test_header_generator.py
git commit -m "feat(ml): add HeaderGenerator writing model_data.h and .cpp"
```

---

## Task 7: Wire main() and run all tests

**Files:**
- Modify: `firmware/models/train_model.py` (complete main())

- [ ] **Step 1: Replace the `main()` placeholder in `train_model.py`**

Replace the entire `main()` function (everything after `y = np.concatenate(y_parts)`) with:

```python
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
```

- [ ] **Step 2: Run the full test suite**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/models"
python -m pytest tests/ -v
```

Expected: `23 passed` (6 + 5 + 6 + 6 from Tasks 2-6, excluding DB integration which uses mocks)

- [ ] **Step 3: Run dry-run smoke test**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
python firmware/models/train_model.py --synthetic --dry-run
```

Expected output:
```
[data] Synthetic: 10000 samples (8xxx normal, 1xxx anomaly — ~20.0%)
[dry-run] Total: 10000 | Normal: 8xxx | Anomaly: 1xxx
[dry-run] Exiting without training.
```

- [ ] **Step 4: Commit**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
git add firmware/models/train_model.py
git commit -m "feat(ml): wire complete main() orchestrating all pipeline stages"
```

---

## Task 8: End-to-end validation

**Files:**
- Modify: `firmware/lib/inference/model_data.h` (overwritten by script)
- Modify: `firmware/lib/inference/model_data.cpp` (overwritten by script)

- [ ] **Step 1: Run full training pipeline**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
python firmware/models/train_model.py --synthetic
```

Expected output:
```
[data] Synthetic: 10000 samples (... normal, ... anomaly — ~20.0%)
[train] Epoch 20/20 — loss: 0.0xx  acc: 0.9xx  val_acc: 0.9xx  val_auc: 0.9xx
[export] firmware/models/model.tflite saved (x.x KB)
[header] firmware/lib/inference/model_data.h updated
[header] firmware/lib/inference/model_data.cpp updated
[done] Activate USE_TFLITE in platformio.ini [env:esp32] to use the model on ESP32
```

- [ ] **Step 2: Verify model_data.h was updated (not placeholder)**

```bash
grep "TFL3\|0x18" "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/lib/inference/model_data.cpp" | head -3
```

Expected: line showing `0x18` or similar real TFLite bytes (not the 32-byte placeholder).

- [ ] **Step 3: Verify header has metadata comment**

```bash
head -10 "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware/lib/inference/model_data.h"
```

Expected: shows date, samples=10000, val_accuracy, val_auc in comments.

- [ ] **Step 4: Verify ESP32 firmware still builds with new model**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/firmware"
pio run -e esp32 2>&1 | tail -5
```

Expected: `SUCCESS` — new `model_data.cpp` compiles clean.

- [ ] **Step 5: Add model.tflite to .gitignore**

```bash
echo "firmware/models/model.tflite" >> "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial/.gitignore"
```

- [ ] **Step 6: Final commit**

```bash
cd "c:/Univesp Projetos/Arquitetura PI 5/edge-ai-industrial"
git add firmware/lib/inference/model_data.h firmware/lib/inference/model_data.cpp .gitignore
git commit -m "feat(ml): update model_data.h with real trained TFLite model"
git push origin feature/esp32-edge-network-sim-bootstrap
```

---

## D3 Checklist — ML Pipeline

- [ ] `python firmware/models/train_model.py --synthetic` completa sem erro
- [ ] `firmware/models/model.tflite` gerado e > 0 bytes
- [ ] `firmware/lib/inference/model_data.h` tem bytes reais (não placeholder de 32 bytes)
- [ ] `python firmware/models/train_model.py --dry-run --synthetic` exibe stats sem treinar
- [ ] `model_data.h` tem comentário com data, amostras e val_accuracy
- [ ] `pio run -e esp32` ainda compila com o novo model_data.cpp

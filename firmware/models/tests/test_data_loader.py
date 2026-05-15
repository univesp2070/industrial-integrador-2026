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

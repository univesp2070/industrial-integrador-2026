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


def test_export_with_quantize_creates_valid_file():
    # For tiny models (~73 params), INT8 quantization overhead can exceed weight savings,
    # so we only verify the INT8 export produces a valid non-empty file.
    model, X = _trained_model()
    with tempfile.TemporaryDirectory() as tmpdir:
        path_int8 = os.path.join(tmpdir, "model_int8.tflite")
        tflite_bytes = TFLiteExporter(output_path=path_int8, quantize=True).export(model, X)
        assert os.path.exists(path_int8), "INT8 model.tflite was not created"
        assert os.path.getsize(path_int8) > 100, "INT8 model.tflite is too small"
        assert isinstance(tflite_bytes, bytes) and len(tflite_bytes) > 100

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

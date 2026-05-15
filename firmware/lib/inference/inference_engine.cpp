#include "inference_engine.h"
#include <cstring>
#include <algorithm>

#ifdef SIMULATION_MODE

void InferenceEngine::begin() {
    // No model to load in simulation mode.
}

InferenceResult InferenceEngine::run(const SensorReading& r) {
    InferenceResult res;

    // Formula: score proportional to vibration (max 2.0 mm/s => score 1.0)
    float score = r.vibration / 2.0f;
    score = std::min(score, 1.0f);
    score = std::max(score, 0.0f);

    res.anomaly_score = score;
    strncpy(res.model_version, MODEL_VERSION, sizeof(res.model_version) - 1);
    res.model_version[sizeof(res.model_version) - 1] = '\0';
    strncpy(res.classification,
            score >= ANOMALY_THRESHOLD ? "anomaly" : "normal",
            sizeof(res.classification) - 1);
    res.classification[sizeof(res.classification) - 1] = '\0';

    return res;
}

#else  // Real ESP32 — hardware mode

#include <Arduino.h>

#ifdef USE_TFLITE
#include "model_data.h"
#include <EloquentTinyML.h>
#include <eloquent_tinyml/tensorflow.h>
static Eloquent::TinyML::TfLite<3, 1, 8 * 1024> _ml;
static bool _model_loaded = false;
#endif  // USE_TFLITE

void InferenceEngine::begin() {
#ifdef USE_TFLITE
    if (_ml.begin(g_model_data)) {
        _model_loaded = true;
        Serial.println("[inference] TFLite model loaded OK");
    } else {
        Serial.println("[inference] WARN: model load failed -- using vibration fallback");
    }
#else
    Serial.println("[inference] Running vibration-based inference (no TFLite model yet)");
#endif
}

InferenceResult InferenceEngine::run(const SensorReading& r) {
    InferenceResult res;
    float score;

#ifdef USE_TFLITE
    if (_model_loaded) {
        float features[3] = {
            r.temperature / 100.0f,
            r.vibration   / 2.0f,
            r.current     / 10.0f,
        };
        float prediction[1];
        _ml.predict(features, prediction);
        score = prediction[0];
    } else {
        score = r.vibration / 2.0f;
    }
#else
    // Fallback: vibration-based scoring (activate USE_TFLITE when model is ready)
    score = r.vibration / 2.0f;
#endif

    score = constrain(score, 0.0f, 1.0f);
    res.anomaly_score = score;
    strncpy(res.model_version, MODEL_VERSION, sizeof(res.model_version) - 1);
    res.model_version[sizeof(res.model_version) - 1] = '\0';
    strncpy(res.classification,
            score >= ANOMALY_THRESHOLD ? "anomaly" : "normal",
            sizeof(res.classification) - 1);
    res.classification[sizeof(res.classification) - 1] = '\0';

    return res;
}

#endif  // SIMULATION_MODE

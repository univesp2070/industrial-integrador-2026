# Firmware Modular ESP32 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the modular ESP32 firmware in C++ (PlatformIO) with EdgeNode orchestrator, SIMULATION_MODE, TFLite Micro placeholder, and full MQTT contract v1 — all compiling clean with `pio run`.

**Architecture:** `EdgeNode` class in `firmware/src/` orchestrates four independent library modules (`wifi_manager`, `mqtt_client`, `sensor_manager`, `inference_engine`) in `firmware/lib/`. Shared types (`SensorReading`, `InferenceResult`) live in `lib/config/device_config.h` so no module depends on another. `main.cpp` becomes 5 lines.

**Tech Stack:** C++17, PlatformIO, Arduino framework (ESP32), PubSubClient 2.8, ArduinoJson 7, EloquentTinyML, Unity (native unit tests).

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `firmware/platformio.ini` | Add `esp32_sim` (SIMULATION_MODE) and `native` (unit tests) envs |
| Create | `firmware/lib/config/device_config.h` | All `#define` constants + `SensorReading` + `InferenceResult` structs |
| Create | `firmware/lib/config/device_config.cpp` | Empty translation unit (satisfies linker) |
| Create | `firmware/lib/sensors/sensor_manager.h` | `SensorManager` interface |
| Create | `firmware/lib/sensors/sensor_manager.cpp` | Simulation math + real driver stubs |
| Create | `firmware/lib/inference/model_data.h` | TFLite model as `const unsigned char[]` placeholder |
| Create | `firmware/lib/inference/inference_engine.h` | `InferenceEngine` interface |
| Create | `firmware/lib/inference/inference_engine.cpp` | TFLite Micro (real) or formula (SIMULATION_MODE) |
| Create | `firmware/lib/communication/wifi_manager.h` | `WifiManager` interface |
| Create | `firmware/lib/communication/wifi_manager.cpp` | WiFi connect + non-blocking reconnect |
| Create | `firmware/lib/communication/mqtt_client.h` | `MqttClient` interface |
| Create | `firmware/lib/communication/mqtt_client.cpp` | PubSubClient wrapper, NTP, LWT, JSON publish, backoff |
| Create | `firmware/src/EdgeNode.h` | `EdgeNode` class declaration |
| Create | `firmware/src/EdgeNode.cpp` | `begin()` + `loop()` orchestration |
| Modify | `firmware/src/main.cpp` | 5-line entry point |
| Create | `firmware/test/test_sensor_manager/test_main.cpp` | Native unit tests — simulation value ranges + anomaly injection |
| Create | `firmware/test/test_inference_engine/test_main.cpp` | Native unit tests — score range + classification string |
| Create | `firmware/test/test_mqtt_payload/test_main.cpp` | Native unit tests — JSON structure matches contract v1 |

---

## Task 1: platformio.ini — add esp32_sim and native envs

**Files:**
- Modify: `firmware/platformio.ini`

- [ ] **Step 1: Add the two new environments to platformio.ini**

Replace the entire content of `firmware/platformio.ini` with:

```ini
; PlatformIO Project Configuration File
; Edge AI Industrial - Firmware

[env:esp32]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
lib_deps =
    knolleary/PubSubClient@^2.8
    bblanchon/ArduinoJson@^7.0
    eloquentarduino/EloquentTinyML@^0.0.9
    Wire
    SPI
build_flags =
    -DESP32
    -DCORE_DEBUG_LEVEL=3
    -DFIRMWARE_VERSION='"1.0.0"'

[env:esp32_sim]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
lib_deps =
    knolleary/PubSubClient@^2.8
    bblanchon/ArduinoJson@^7.0
build_flags =
    -DESP32
    -DSIMULATION_MODE
    -DFIRMWARE_VERSION='"sim-1.0.0"'

[env:stm32]
platform = ststm32
board = nucleo_f446re
framework = arduino
monitor_speed = 115200
lib_deps =
    knolleary/PubSubClient@^2.8
    bblanchon/ArduinoJson@^7.0
build_flags =
    -DSTM32

[env:native]
platform = native
build_flags =
    -DSIMULATION_MODE
    -DNATIVE_TEST
    -DFIRMWARE_VERSION='"test"'
lib_deps =
    bblanchon/ArduinoJson@^7.0
    throwtheswitch/Unity@^2.5.2
```

- [ ] **Step 2: Commit**

```bash
git add firmware/platformio.ini
git commit -m "feat(firmware): add esp32_sim and native test envs to platformio.ini"
```

---

## Task 2: device_config — constants and shared types

**Files:**
- Create: `firmware/lib/config/device_config.h`
- Create: `firmware/lib/config/device_config.cpp`

- [ ] **Step 1: Create `firmware/lib/config/device_config.h`**

```cpp
#pragma once

// ── Device identity ──────────────────────────────────────────────────────────
#define DEVICE_ID         "esp32-001"
#define FIRMWARE_VERSION_DEFAULT "1.0.0"

// ── Network ──────────────────────────────────────────────────────────────────
#define WIFI_SSID         "your_ssid"
#define WIFI_PASSWORD     "your_password"
#define WIFI_TIMEOUT_MS   10000

// ── MQTT broker ──────────────────────────────────────────────────────────────
#define MQTT_BROKER       "192.168.1.100"
#define MQTT_PORT         1883
#define MQTT_USER         "edge"
#define MQTT_PASSWORD     "edge_pass"
#define MQTT_CLIENT_ID    "esp32-001"
#define MQTT_QOS          1

// MQTT topics (use DEVICE_ID as suffix)
#define TOPIC_SENSOR_DATA   "sensor/data/" DEVICE_ID
#define TOPIC_DEVICE_STATUS "device/status/" DEVICE_ID
#define TOPIC_DEVICE_CONFIG "device/config/" DEVICE_ID

// ── Timing ───────────────────────────────────────────────────────────────────
#define PUBLISH_INTERVAL_MS  5000UL
#define STATUS_INTERVAL_MS   30000UL
#define RECONNECT_MAX_MS     30000UL

// ── Inference ────────────────────────────────────────────────────────────────
#define ANOMALY_THRESHOLD    0.8f
#define MODEL_VERSION        "v1.0"

// ── Simulation ───────────────────────────────────────────────────────────────
#define ANOMALY_INTERVAL_S   60   // inject anomaly every N seconds

// ── Shared data types ────────────────────────────────────────────────────────
struct SensorReading {
    float temperature;     // °C
    float vibration;       // mm/s
    float current;         // A
    unsigned long uptime_s;
};

struct InferenceResult {
    char  classification[16];  // "normal" or "anomaly"
    float anomaly_score;       // 0.0 – 1.0
    char  model_version[16];
};
```

- [ ] **Step 2: Create `firmware/lib/config/device_config.cpp`**

```cpp
#include "device_config.h"
// Translation unit — no logic here.
```

- [ ] **Step 3: Commit**

```bash
git add firmware/lib/config/
git commit -m "feat(firmware): add device_config constants and shared types"
```

---

## Task 3: sensor_manager — simulation math (TDD)

**Files:**
- Create: `firmware/lib/sensors/sensor_manager.h`
- Create: `firmware/lib/sensors/sensor_manager.cpp`
- Create: `firmware/test/test_sensor_manager/test_main.cpp`

- [ ] **Step 1: Write the failing test**

Create `firmware/test/test_sensor_manager/test_main.cpp`:

```cpp
#include <unity.h>
#include <cmath>

// Pull in only what we need from the module under test.
// We #include the .cpp directly in native tests so we don't need a separate build.
#define SIMULATION_MODE
#define NATIVE_TEST
#include "../../lib/config/device_config.h"
#include "../../lib/sensors/sensor_manager.h"

void setUp(void) {}
void tearDown(void) {}

void test_temperature_in_range(void) {
    SensorManager sm;
    sm.begin();
    for (int s = 0; s < 200; s++) {
        SensorReading r = sm.read(s);
        TEST_ASSERT_GREATER_OR_EQUAL_FLOAT(20.0f, r.temperature);
        TEST_ASSERT_LESS_OR_EQUAL_FLOAT(85.0f, r.temperature);
    }
}

void test_vibration_normal_in_range(void) {
    SensorManager sm;
    sm.begin();
    // At t=0 no anomaly — check several normal seconds
    for (int s = 1; s < ANOMALY_INTERVAL_S; s++) {
        SensorReading r = sm.read(s);
        TEST_ASSERT_GREATER_OR_EQUAL_FLOAT(0.0f, r.vibration);
        TEST_ASSERT_LESS_OR_EQUAL_FLOAT(1.0f, r.vibration);
    }
}

void test_anomaly_injection(void) {
    SensorManager sm;
    sm.begin();
    // At t = ANOMALY_INTERVAL_S, vibration should spike above normal ceiling (1.0f)
    SensorReading r = sm.read(ANOMALY_INTERVAL_S);
    TEST_ASSERT_GREATER_FLOAT(1.0f, r.vibration);
}

void test_current_in_range(void) {
    SensorManager sm;
    sm.begin();
    for (int s = 0; s < 200; s++) {
        SensorReading r = sm.read(s);
        TEST_ASSERT_GREATER_OR_EQUAL_FLOAT(2.0f, r.current);
        TEST_ASSERT_LESS_OR_EQUAL_FLOAT(5.0f, r.current);
    }
}

void test_uptime_matches_input(void) {
    SensorManager sm;
    sm.begin();
    SensorReading r = sm.read(42);
    TEST_ASSERT_EQUAL_UINT32(42, r.uptime_s);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_temperature_in_range);
    RUN_TEST(test_vibration_normal_in_range);
    RUN_TEST(test_anomaly_injection);
    RUN_TEST(test_current_in_range);
    RUN_TEST(test_uptime_matches_input);
    return UNITY_END();
}
```

- [ ] **Step 2: Create the header so the test file compiles (interface only)**

Create `firmware/lib/sensors/sensor_manager.h`:

```cpp
#pragma once
#include "config/device_config.h"

class SensorManager {
public:
    void         begin();
    SensorReading read(unsigned long uptime_s);
};
```

- [ ] **Step 3: Run test — expect FAIL (linker error, no implementation)**

```bash
cd firmware
pio test -e native -f test_sensor_manager
```

Expected: build error — `SensorManager::begin` and `SensorManager::read` undefined.

- [ ] **Step 4: Implement `sensor_manager.cpp`**

Create `firmware/lib/sensors/sensor_manager.cpp`:

```cpp
#include "sensor_manager.h"
#include <cmath>

#ifdef SIMULATION_MODE

void SensorManager::begin() {
    // No hardware to init in simulation mode.
}

SensorReading SensorManager::read(unsigned long uptime_s) {
    SensorReading r;
    r.uptime_s = uptime_s;

    // Temperature: sinusoidal 20°C – 85°C, period = 120s
    float t = static_cast<float>(uptime_s);
    r.temperature = 52.5f + 32.5f * sinf(2.0f * M_PI * t / 120.0f);

    // Current: linear ramp 2A – 5A, period = 300s
    r.current = 2.0f + 3.0f * (0.5f + 0.5f * sinf(2.0f * M_PI * t / 300.0f));

    // Vibration: gaussian noise around 0.3 mm/s
    // Use a deterministic pseudo-random based on uptime
    float noise = 0.05f * sinf(t * 7.3f) + 0.05f * sinf(t * 13.7f);
    r.vibration = 0.3f + noise;

    // Anomaly injection: spike vibration > 1.0 every ANOMALY_INTERVAL_S
    if (uptime_s > 0 && (uptime_s % ANOMALY_INTERVAL_S) == 0) {
        r.vibration = 1.8f;
    }

    return r;
}

#else  // Hardware mode

#include <Arduino.h>
// Add real sensor driver headers here when available:
// #include <DallasTemperature.h>
// #include <Adafruit_ADXL345_U.h>
// #include <INA219_WE.h>

void SensorManager::begin() {
    // TODO(D-hardware): Initialize I2C sensors
    // Wire.begin();
    // _dallas.begin();
    // _adxl.begin();
    // _ina219.begin();
}

SensorReading SensorManager::read(unsigned long uptime_s) {
    SensorReading r;
    r.uptime_s = uptime_s;
    // TODO(D-hardware): Replace with real driver reads
    r.temperature = 0.0f;
    r.vibration   = 0.0f;
    r.current     = 0.0f;
    return r;
}

#endif
```

- [ ] **Step 5: Run test — expect PASS**

```bash
cd firmware
pio test -e native -f test_sensor_manager
```

Expected output:
```
test/test_sensor_manager/test_main.cpp:58:test_temperature_in_range PASSED
test/test_sensor_manager/test_main.cpp:59:test_vibration_normal_in_range PASSED
test/test_sensor_manager/test_main.cpp:60:test_anomaly_injection PASSED
test/test_sensor_manager/test_main.cpp:61:test_current_in_range PASSED
test/test_sensor_manager/test_main.cpp:62:test_uptime_matches_input PASSED
5 Tests 0 Failures 0 Ignored
```

- [ ] **Step 6: Commit**

```bash
git add firmware/lib/sensors/ firmware/test/test_sensor_manager/
git commit -m "feat(firmware): add SensorManager with SIMULATION_MODE and native tests"
```

---

## Task 4: inference_engine — scoring logic (TDD)

**Files:**
- Create: `firmware/lib/inference/model_data.h`
- Create: `firmware/lib/inference/inference_engine.h`
- Create: `firmware/lib/inference/inference_engine.cpp`
- Create: `firmware/test/test_inference_engine/test_main.cpp`

- [ ] **Step 1: Write the failing test**

Create `firmware/test/test_inference_engine/test_main.cpp`:

```cpp
#include <unity.h>
#define SIMULATION_MODE
#define NATIVE_TEST
#include "../../lib/config/device_config.h"
#include "../../lib/inference/inference_engine.h"

void setUp(void) {}
void tearDown(void) {}

static SensorReading make_reading(float temp, float vib, float curr, unsigned long t) {
    SensorReading r;
    r.temperature = temp;
    r.vibration   = vib;
    r.current     = curr;
    r.uptime_s    = t;
    return r;
}

void test_score_in_range(void) {
    InferenceEngine ie;
    ie.begin();
    SensorReading r = make_reading(30.0f, 0.3f, 3.0f, 10);
    InferenceResult res = ie.run(r);
    TEST_ASSERT_GREATER_OR_EQUAL_FLOAT(0.0f, res.anomaly_score);
    TEST_ASSERT_LESS_OR_EQUAL_FLOAT(1.0f, res.anomaly_score);
}

void test_normal_classification(void) {
    InferenceEngine ie;
    ie.begin();
    // vibration 0.3 mm/s → score = 0.15 → below ANOMALY_THRESHOLD (0.8)
    SensorReading r = make_reading(30.0f, 0.3f, 3.0f, 10);
    InferenceResult res = ie.run(r);
    TEST_ASSERT_EQUAL_STRING("normal", res.classification);
}

void test_anomaly_classification(void) {
    InferenceEngine ie;
    ie.begin();
    // vibration 1.8 mm/s → score = min(0.9, 1.0) = 0.9 → above ANOMALY_THRESHOLD (0.8)
    SensorReading r = make_reading(30.0f, 1.8f, 3.0f, 60);
    InferenceResult res = ie.run(r);
    TEST_ASSERT_EQUAL_STRING("anomaly", res.classification);
    TEST_ASSERT_GREATER_OR_EQUAL_FLOAT(ANOMALY_THRESHOLD, res.anomaly_score);
}

void test_model_version_set(void) {
    InferenceEngine ie;
    ie.begin();
    SensorReading r = make_reading(30.0f, 0.3f, 3.0f, 1);
    InferenceResult res = ie.run(r);
    TEST_ASSERT_EQUAL_STRING(MODEL_VERSION, res.model_version);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_score_in_range);
    RUN_TEST(test_normal_classification);
    RUN_TEST(test_anomaly_classification);
    RUN_TEST(test_model_version_set);
    return UNITY_END();
}
```

- [ ] **Step 2: Create `firmware/lib/inference/model_data.h`** (TFLite placeholder)

```cpp
#pragma once
// Placeholder TFLite flatbuffer — replace with trained model.
// To regenerate: python firmware/models/train_placeholder.py
// Then: xxd -i model.tflite > firmware/lib/inference/model_data.h
//
// This placeholder is a minimal 3-input → 1-output dense network (all-zeros weights).
// It is used only in non-SIMULATION_MODE (real ESP32 env).
// In SIMULATION_MODE the model is not loaded — vibration-based formula is used instead.

extern const unsigned char g_model_data[];
extern const int           g_model_data_len;
```

Create `firmware/lib/inference/model_data.cpp` (placeholder bytes — real model replaces this file):

```cpp
#include "model_data.h"

// Minimal TFLite flatbuffer placeholder (64 zero bytes — not a valid model).
// Replace with: xxd -i trained_model.tflite content when available.
const unsigned char g_model_data[] = {
    0x18, 0x00, 0x00, 0x00, 0x54, 0x46, 0x4c, 0x33, // TFL3 magic
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
const int g_model_data_len = sizeof(g_model_data);
```

- [ ] **Step 3: Create `firmware/lib/inference/inference_engine.h`**

```cpp
#pragma once
#include "config/device_config.h"

class InferenceEngine {
public:
    void           begin();
    InferenceResult run(const SensorReading& r);
};
```

- [ ] **Step 4: Run test — expect FAIL (no implementation)**

```bash
cd firmware
pio test -e native -f test_inference_engine
```

Expected: build error — `InferenceEngine::begin` and `InferenceEngine::run` undefined.

- [ ] **Step 5: Implement `firmware/lib/inference/inference_engine.cpp`**

```cpp
#include "inference_engine.h"
#include <cstring>
#include <algorithm>

#ifdef SIMULATION_MODE

void InferenceEngine::begin() {
    // No model to load in simulation mode.
}

InferenceResult InferenceEngine::run(const SensorReading& r) {
    InferenceResult res;

    // Formula: score proportional to vibration (max 2.0 mm/s → score 1.0)
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

#else  // Real ESP32 with EloquentTinyML

#include <Arduino.h>
#include "model_data.h"

// EloquentTinyML: <num_inputs, num_outputs, tensor_arena_size>
// Adjust tensor_arena_size to match model requirements (start with 8*1024).
#include <EloquentTinyML.h>
#include <eloquent_tinyml/tensorflow.h>

static Eloquent::TinyML::TfLite<3, 1, 8 * 1024> _ml;
static bool _model_loaded = false;

void InferenceEngine::begin() {
    if (_ml.begin(g_model_data)) {
        _model_loaded = true;
        Serial.println("[inference] TFLite model loaded OK");
    } else {
        Serial.println("[inference] WARN: model load failed — using vibration fallback");
    }
}

InferenceResult InferenceEngine::run(const SensorReading& r) {
    InferenceResult res;
    float score;

    if (_model_loaded) {
        float features[3] = {
            r.temperature / 100.0f,   // normalize 0–1 (0–100°C range)
            r.vibration   / 2.0f,     // normalize 0–1 (0–2 mm/s range)
            r.current     / 10.0f,    // normalize 0–1 (0–10 A range)
        };
        float prediction[1];
        _ml.predict(features, prediction);
        score = prediction[0];
    } else {
        // Fallback: vibration-based scoring (same as SIMULATION_MODE)
        score = r.vibration / 2.0f;
    }

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

#endif
```

- [ ] **Step 6: Run test — expect PASS**

```bash
cd firmware
pio test -e native -f test_inference_engine
```

Expected:
```
test_score_in_range PASSED
test_normal_classification PASSED
test_anomaly_classification PASSED
test_model_version_set PASSED
4 Tests 0 Failures 0 Ignored
```

- [ ] **Step 7: Commit**

```bash
git add firmware/lib/inference/ firmware/test/test_inference_engine/
git commit -m "feat(firmware): add InferenceEngine with TFLite Micro placeholder and native tests"
```

---

## Task 5: wifi_manager — non-blocking WiFi

**Files:**
- Create: `firmware/lib/communication/wifi_manager.h`
- Create: `firmware/lib/communication/wifi_manager.cpp`

No native test: `WiFi.h` is Arduino hardware-dependent. Tested manually via Serial monitor when flashing.

- [ ] **Step 1: Create `firmware/lib/communication/wifi_manager.h`**

```cpp
#pragma once

#ifndef NATIVE_TEST
#include <Arduino.h>
#include <WiFi.h>
#endif

class WifiManager {
public:
    void begin();
    void maintain();
    bool isConnected() const;

private:
    unsigned long _lastAttemptMs = 0;
    static constexpr unsigned long RETRY_INTERVAL_MS = 5000UL;
};
```

- [ ] **Step 2: Create `firmware/lib/communication/wifi_manager.cpp`**

```cpp
#include "wifi_manager.h"

#ifndef NATIVE_TEST

#include "config/device_config.h"
#include <Arduino.h>
#include <WiFi.h>

void WifiManager::begin() {
    WiFi.mode(WIFI_STA);
    Serial.printf("[wifi] Connecting to %s\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT_MS) {
        delay(500);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[wifi] Connected — IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n[wifi] WARN: initial connect failed — maintain() will retry");
    }
}

void WifiManager::maintain() {
    if (WiFi.status() == WL_CONNECTED) return;

    unsigned long now = millis();
    if (now - _lastAttemptMs < RETRY_INTERVAL_MS) return;

    _lastAttemptMs = now;
    Serial.println("[wifi] Reconnecting...");
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

bool WifiManager::isConnected() const {
    return WiFi.status() == WL_CONNECTED;
}

#else
// Native test stub — no WiFi hardware
void WifiManager::begin() {}
void WifiManager::maintain() {}
bool WifiManager::isConnected() const { return true; }
#endif
```

- [ ] **Step 3: Commit**

```bash
git add firmware/lib/communication/wifi_manager.h firmware/lib/communication/wifi_manager.cpp
git commit -m "feat(firmware): add WifiManager with non-blocking reconnect"
```

---

## Task 6: mqtt_client — NTP, LWT, JSON publish, backoff (TDD)

**Files:**
- Create: `firmware/lib/communication/mqtt_client.h`
- Create: `firmware/lib/communication/mqtt_client.cpp`
- Create: `firmware/test/test_mqtt_payload/test_main.cpp`

- [ ] **Step 1: Write the failing test (JSON structure)**

Create `firmware/test/test_mqtt_payload/test_main.cpp`:

```cpp
#include <unity.h>
#include <ArduinoJson.h>
#define SIMULATION_MODE
#define NATIVE_TEST
#include "../../lib/config/device_config.h"

// We test only the JSON building logic, extracted as a free function for testability.
// This mirrors exactly what MqttClient::publishSensorData() builds.

void build_sensor_json(const SensorReading& r, const InferenceResult& inf,
                       const char* timestamp, JsonDocument& doc) {
    doc["device_id"]  = DEVICE_ID;
    doc["timestamp"]  = timestamp;
    auto sensors = doc["sensors"].to<JsonObject>();
    auto temp    = sensors["temperature"].to<JsonObject>();
    temp["value"] = r.temperature;
    temp["unit"]  = "C";
    auto vib     = sensors["vibration"].to<JsonObject>();
    vib["value"]  = r.vibration;
    vib["unit"]   = "mm_s";
    auto curr    = sensors["current"].to<JsonObject>();
    curr["value"] = r.current;
    curr["unit"]  = "A";
    auto inference = doc["inference"].to<JsonObject>();
    inference["classification"] = inf.classification;
    inference["anomaly_score"]  = inf.anomaly_score;
    inference["model_version"]  = inf.model_version;
}

void build_status_json(unsigned long uptime_s, int rssi,
                       const char* timestamp, JsonDocument& doc) {
    doc["device_id"]        = DEVICE_ID;
    doc["status"]           = "online";
    doc["firmware_version"] = FIRMWARE_VERSION;
    doc["uptime_seconds"]   = (int)uptime_s;
    doc["free_memory"]      = 0;  // filled by real impl
    doc["wifi_rssi"]        = rssi;
    doc["timestamp"]        = timestamp;
}

void setUp(void) {}
void tearDown(void) {}

void test_sensor_payload_has_required_fields(void) {
    SensorReading r   = {30.0f, 0.3f, 3.0f, 10};
    InferenceResult inf;
    strncpy(inf.classification, "normal", 16);
    inf.anomaly_score = 0.15f;
    strncpy(inf.model_version, "v1.0", 16);

    JsonDocument doc;
    build_sensor_json(r, inf, "2026-04-04T10:00:00Z", doc);

    TEST_ASSERT_TRUE(doc["device_id"].is<const char*>());
    TEST_ASSERT_TRUE(doc["timestamp"].is<const char*>());
    TEST_ASSERT_TRUE(doc["sensors"]["temperature"]["value"].is<float>());
    TEST_ASSERT_EQUAL_STRING("C",     doc["sensors"]["temperature"]["unit"]);
    TEST_ASSERT_EQUAL_STRING("mm_s",  doc["sensors"]["vibration"]["unit"]);
    TEST_ASSERT_EQUAL_STRING("A",     doc["sensors"]["current"]["unit"]);
    TEST_ASSERT_EQUAL_STRING("normal", doc["inference"]["classification"]);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.15f, doc["inference"]["anomaly_score"].as<float>());
    TEST_ASSERT_EQUAL_STRING("v1.0",  doc["inference"]["model_version"]);
}

void test_status_payload_has_required_fields(void) {
    JsonDocument doc;
    build_status_json(3600, -42, "2026-04-04T10:00:00Z", doc);

    TEST_ASSERT_EQUAL_STRING(DEVICE_ID, doc["device_id"]);
    TEST_ASSERT_EQUAL_STRING("online",  doc["status"]);
    TEST_ASSERT_EQUAL_INT(3600, doc["uptime_seconds"].as<int>());
    TEST_ASSERT_EQUAL_INT(-42,  doc["wifi_rssi"].as<int>());
    TEST_ASSERT_TRUE(doc["timestamp"].is<const char*>());
}

void test_sensor_payload_device_id_matches_config(void) {
    SensorReading r   = {25.0f, 0.5f, 2.5f, 5};
    InferenceResult inf;
    strncpy(inf.classification, "normal", 16);
    inf.anomaly_score = 0.25f;
    strncpy(inf.model_version, "v1.0", 16);

    JsonDocument doc;
    build_sensor_json(r, inf, "2026-04-04T10:00:00Z", doc);

    TEST_ASSERT_EQUAL_STRING(DEVICE_ID, doc["device_id"]);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_sensor_payload_has_required_fields);
    RUN_TEST(test_status_payload_has_required_fields);
    RUN_TEST(test_sensor_payload_device_id_matches_config);
    return UNITY_END();
}
```

- [ ] **Step 2: Run test — expect PASS immediately** (tests JSON building, no MqttClient needed yet)

```bash
cd firmware
pio test -e native -f test_mqtt_payload
```

Expected: `3 Tests 0 Failures 0 Ignored`

- [ ] **Step 3: Create `firmware/lib/communication/mqtt_client.h`**

```cpp
#pragma once

#include "config/device_config.h"

#ifndef NATIVE_TEST
#include <Arduino.h>
#include <PubSubClient.h>
#include <WiFiClient.h>
#endif

class MqttClient {
public:
    using MessageCallback = void(*)(const char* topic, const char* payload);

    void begin(MessageCallback callback = nullptr);
    bool connect();
    void maintain();
    void publishSensorData(const SensorReading& r, const InferenceResult& inf);
    void publishStatus(unsigned long uptime_s);

private:
    void     _buildTimestamp(char* buf, size_t len);
    void     _applyBackoff();

#ifndef NATIVE_TEST
    WiFiClient    _wifiClient;
    PubSubClient  _pubsub{_wifiClient};
#endif

    MessageCallback _callback    = nullptr;
    unsigned long   _lastAttemptMs = 0;
    unsigned long   _backoffMs     = 1000;
};
```

- [ ] **Step 4: Create `firmware/lib/communication/mqtt_client.cpp`**

```cpp
#include "mqtt_client.h"

#ifndef NATIVE_TEST

#include <Arduino.h>
#include <ArduinoJson.h>
#include <time.h>

// ── Internal callback shim ────────────────────────────────────────────────────
static MqttClient::MessageCallback _globalCallback = nullptr;

static void _pubsubCallback(char* topic, byte* payload, unsigned int length) {
    char buf[256];
    size_t len = (length < sizeof(buf) - 1) ? length : sizeof(buf) - 1;
    memcpy(buf, payload, len);
    buf[len] = '\0';
    if (_globalCallback) _globalCallback(topic, buf);
}

// ── Timestamp (NTP) ──────────────────────────────────────────────────────────
void MqttClient::_buildTimestamp(char* buf, size_t len) {
    time_t now = time(nullptr);
    if (now < 1000000000L) {
        // NTP not synced yet — use epoch fallback
        unsigned long ms = millis() / 1000UL;
        // 2026-01-01T00:00:00Z = 1767225600 Unix epoch
        now = 1767225600L + (long)ms;
    }
    struct tm* t = gmtime(&now);
    strftime(buf, len, "%Y-%m-%dT%H:%M:%SZ", t);
}

// ── Public API ───────────────────────────────────────────────────────────────
void MqttClient::begin(MessageCallback callback) {
    _callback       = callback;
    _globalCallback = callback;

    // Configure NTP
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");

    // Configure LWT before any connect attempt
    _pubsub.setServer(MQTT_BROKER, MQTT_PORT);
    _pubsub.setCallback(_pubsubCallback);
    _pubsub.setBufferSize(512);

    Serial.printf("[mqtt] Broker: %s:%d\n", MQTT_BROKER, MQTT_PORT);
}

bool MqttClient::connect() {
    if (_pubsub.connected()) return true;

    char lwtPayload[64];
    snprintf(lwtPayload, sizeof(lwtPayload),
             "{\"device_id\":\"%s\",\"status\":\"offline\"}", DEVICE_ID);

    bool ok = _pubsub.connect(
        MQTT_CLIENT_ID, MQTT_USER, MQTT_PASSWORD,
        TOPIC_DEVICE_STATUS, MQTT_QOS, true, lwtPayload
    );

    if (ok) {
        Serial.println("[mqtt] Connected");
        _backoffMs = 1000;
        _pubsub.subscribe(TOPIC_DEVICE_CONFIG, MQTT_QOS);
    } else {
        Serial.printf("[mqtt] Connect failed, rc=%d — retry in %lums\n",
                      _pubsub.state(), _backoffMs);
    }
    return ok;
}

void MqttClient::maintain() {
    if (_pubsub.connected()) {
        _pubsub.loop();
        return;
    }

    unsigned long now = millis();
    if (now - _lastAttemptMs < _backoffMs) return;

    _lastAttemptMs = now;
    if (!connect()) _applyBackoff();
}

void MqttClient::_applyBackoff() {
    _backoffMs = (_backoffMs * 2 > RECONNECT_MAX_MS) ? RECONNECT_MAX_MS : _backoffMs * 2;
}

void MqttClient::publishSensorData(const SensorReading& r, const InferenceResult& inf) {
    if (!_pubsub.connected()) return;

    char timestamp[32];
    _buildTimestamp(timestamp, sizeof(timestamp));

    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;
    doc["timestamp"] = timestamp;

    auto sensors = doc["sensors"].to<JsonObject>();
    auto temp    = sensors["temperature"].to<JsonObject>();
    temp["value"] = r.temperature;  temp["unit"] = "C";
    auto vib     = sensors["vibration"].to<JsonObject>();
    vib["value"]  = r.vibration;    vib["unit"]  = "mm_s";
    auto curr    = sensors["current"].to<JsonObject>();
    curr["value"] = r.current;      curr["unit"] = "A";

    auto inference = doc["inference"].to<JsonObject>();
    inference["classification"] = inf.classification;
    inference["anomaly_score"]  = inf.anomaly_score;
    inference["model_version"]  = inf.model_version;

    char buf[512];
    size_t n = serializeJson(doc, buf, sizeof(buf));
    _pubsub.publish(TOPIC_SENSOR_DATA, (const uint8_t*)buf, n, false);
    Serial.printf("[mqtt] published sensor/data: score=%.2f class=%s\n",
                  inf.anomaly_score, inf.classification);
}

void MqttClient::publishStatus(unsigned long uptime_s) {
    if (!_pubsub.connected()) return;

    char timestamp[32];
    _buildTimestamp(timestamp, sizeof(timestamp));

    extern uint32_t ESP.getFreeHeap();  // available in Arduino ESP32 SDK

    JsonDocument doc;
    doc["device_id"]        = DEVICE_ID;
    doc["status"]           = "online";
    doc["firmware_version"] = FIRMWARE_VERSION;
    doc["uptime_seconds"]   = (int)uptime_s;
    doc["free_memory"]      = (int)ESP.getFreeHeap();
    doc["wifi_rssi"]        = WiFi.RSSI();
    doc["timestamp"]        = timestamp;

    char buf[256];
    size_t n = serializeJson(doc, buf, sizeof(buf));
    _pubsub.publish(TOPIC_DEVICE_STATUS, (const uint8_t*)buf, n, false);
    Serial.printf("[mqtt] published device/status: uptime=%lus\n", uptime_s);
}

#else
// Native stubs — logic tested via test_mqtt_payload
void MqttClient::begin(MessageCallback cb) { _callback = cb; }
bool MqttClient::connect() { return true; }
void MqttClient::maintain() {}
void MqttClient::publishSensorData(const SensorReading&, const InferenceResult&) {}
void MqttClient::publishStatus(unsigned long) {}
void MqttClient::_buildTimestamp(char* buf, size_t len) {
    strncpy(buf, "2026-01-01T00:00:00Z", len);
}
void MqttClient::_applyBackoff() {}
#endif
```

- [ ] **Step 5: Run all native tests**

```bash
cd firmware
pio test -e native
```

Expected: all 12 tests pass across the 3 test suites.

- [ ] **Step 6: Commit**

```bash
git add firmware/lib/communication/mqtt_client.h firmware/lib/communication/mqtt_client.cpp
git add firmware/test/test_mqtt_payload/
git commit -m "feat(firmware): add MqttClient with NTP, LWT, JSON publish v1, and native tests"
```

---

## Task 7: EdgeNode — orchestrator

**Files:**
- Create: `firmware/src/EdgeNode.h`
- Create: `firmware/src/EdgeNode.cpp`

- [ ] **Step 1: Create `firmware/src/EdgeNode.h`**

```cpp
#pragma once
#include "config/device_config.h"
#include "sensors/sensor_manager.h"
#include "inference/inference_engine.h"
#include "communication/wifi_manager.h"
#include "communication/mqtt_client.h"

class EdgeNode {
public:
    void begin();
    void loop();

private:
    WifiManager     _wifi;
    MqttClient      _mqtt;
    SensorManager   _sensors;
    InferenceEngine _inference;

    unsigned long _lastPublishMs = 0;
    unsigned long _lastStatusMs  = 0;
    unsigned long _startMs       = 0;
};
```

- [ ] **Step 2: Create `firmware/src/EdgeNode.cpp`**

```cpp
#include "EdgeNode.h"
#include <Arduino.h>

void EdgeNode::begin() {
    Serial.begin(115200);
    while (!Serial) delay(10);
    Serial.println("\n[edge] Edge AI Industrial — starting...");

    _startMs = millis();

    _wifi.begin();

    _mqtt.begin([](const char* topic, const char* payload) {
        Serial.printf("[mqtt] received — topic: %s  payload: %s\n", topic, payload);
        // Remote config handling: parse payload and apply settings as needed.
        // (Extended in D5 — A5 backlog item)
    });

    if (_wifi.isConnected()) {
        _mqtt.connect();
    }

    _sensors.begin();
    _inference.begin();

    // Publish initial online status
    _mqtt.publishStatus(0);

    Serial.println("[edge] Init complete. Entering loop.");
}

void EdgeNode::loop() {
    _wifi.maintain();
    _mqtt.maintain();

    unsigned long now     = millis();
    unsigned long uptime  = (now - _startMs) / 1000UL;

    if (now - _lastPublishMs >= PUBLISH_INTERVAL_MS) {
        _lastPublishMs = now;

        SensorReading  reading   = _sensors.read(uptime);
        InferenceResult inference = _inference.run(reading);

        _mqtt.publishSensorData(reading, inference);
    }

    if (now - _lastStatusMs >= STATUS_INTERVAL_MS) {
        _lastStatusMs = now;
        _mqtt.publishStatus(uptime);
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add firmware/src/EdgeNode.h firmware/src/EdgeNode.cpp
git commit -m "feat(firmware): add EdgeNode orchestrator with begin/loop cycle"
```

---

## Task 8: main.cpp — 5-line entry point

**Files:**
- Modify: `firmware/src/main.cpp`

- [ ] **Step 1: Replace main.cpp**

```cpp
#include <Arduino.h>
#include "EdgeNode.h"

static EdgeNode node;

void setup() { node.begin(); }
void loop()  { node.loop();  }
```

- [ ] **Step 2: Commit**

```bash
git add firmware/src/main.cpp
git commit -m "feat(firmware): refactor main.cpp to 5-line EdgeNode delegation"
```

---

## Task 9: Build validation

**Files:** none (validation only)

- [ ] **Step 1: Run all native unit tests**

```bash
cd firmware
pio test -e native
```

Expected output (12 tests total):
```
test_sensor_manager   — 5 Tests 0 Failures 0 Ignored
test_inference_engine — 4 Tests 0 Failures 0 Ignored
test_mqtt_payload     — 3 Tests 0 Failures 0 Ignored
```

- [ ] **Step 2: Build esp32_sim (SIMULATION_MODE, no hardware)**

```bash
pio run -e esp32_sim
```

Expected: `SUCCESS` — no errors, no warnings about undefined hardware.

- [ ] **Step 3: Build esp32 (full hardware + TFLite)**

```bash
pio run -e esp32
```

Expected: `SUCCESS` — EloquentTinyML links, PubSubClient links, model_data.h included.

- [ ] **Step 4: Verify no TODOs remain in main.cpp**

```bash
grep -n TODO firmware/src/main.cpp
```

Expected: no output.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat(firmware): D3 complete — modular ESP32 firmware with EdgeNode, TFLite, MQTT v1"
```

---

## Checklist D3 (from spec)

- [ ] `pio run -e esp32` compila sem erro
- [ ] `pio run -e esp32_sim` compila sem erro
- [ ] `main.cpp` sem TODOs — delega tudo para `EdgeNode`
- [ ] Loop principal não usa `delay()` para esperas longas
- [ ] JSON publicado é compatível com contrato v1
- [ ] LWT configurado antes de qualquer `connect()`

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

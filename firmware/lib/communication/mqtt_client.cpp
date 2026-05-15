#include "mqtt_client.h"

#ifndef NATIVE_TEST

#include <Arduino.h>
#include <WiFi.h>
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
        // NTP not synced yet -- epoch fallback: 2026-01-01T00:00:00Z + uptime
        now = 1767225600L + (long)(millis() / 1000UL);
    }
    struct tm* t = gmtime(&now);
    strftime(buf, len, "%Y-%m-%dT%H:%M:%SZ", t);
}

// ── Public API ───────────────────────────────────────────────────────────────
void MqttClient::begin(MessageCallback callback) {
    _callback       = callback;
    _globalCallback = callback;

    configTime(0, 0, "pool.ntp.org", "time.nist.gov");

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
        Serial.printf("[mqtt] Connect failed, rc=%d -- retry in %lums\n",
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
// Native stubs
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

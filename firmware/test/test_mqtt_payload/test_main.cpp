#include <unity.h>
#include <ArduinoJson.h>
#define SIMULATION_MODE
#define NATIVE_TEST
#if defined(NATIVE_TEST)
#include "../lib/config/device_config.h"
#else
#include "config/device_config.h"
#endif

// Free functions that mirror MqttClient::publishSensorData and publishStatus JSON building.
// Tested independently so the JSON contract can be verified without hardware.

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
    doc["free_memory"]      = 0;
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

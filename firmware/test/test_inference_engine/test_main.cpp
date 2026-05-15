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
    // vibration 0.3 mm/s => score = 0.15 => below ANOMALY_THRESHOLD (0.8)
    SensorReading r = make_reading(30.0f, 0.3f, 3.0f, 10);
    InferenceResult res = ie.run(r);
    TEST_ASSERT_EQUAL_STRING("normal", res.classification);
}

void test_anomaly_classification(void) {
    InferenceEngine ie;
    ie.begin();
    // vibration 1.8 mm/s => score = min(0.9, 1.0) = 0.9 => above ANOMALY_THRESHOLD (0.8)
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

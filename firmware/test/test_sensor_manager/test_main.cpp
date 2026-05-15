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
    TEST_ASSERT_GREATER_THAN_FLOAT(1.0f, r.vibration);
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

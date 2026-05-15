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

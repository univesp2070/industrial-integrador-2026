#pragma once

#if defined(NATIVE_TEST)
#include "../config/device_config.h"
#else
#include "device_config.h"
#endif

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
    void _buildTimestamp(char* buf, size_t len);
    void _applyBackoff();

#ifndef NATIVE_TEST
    WiFiClient    _wifiClient;
    PubSubClient  _pubsub{_wifiClient};
#endif

    MessageCallback _callback     = nullptr;
    unsigned long   _lastAttemptMs = 0;
    unsigned long   _backoffMs     = 1000;
};

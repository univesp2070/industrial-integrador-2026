#pragma once

#ifndef NATIVE_TEST
#include <Arduino.h>
#include <WiFi.h>
#endif

#if defined(NATIVE_TEST)
#include "../config/device_config.h"
#else
#include "device_config.h"
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

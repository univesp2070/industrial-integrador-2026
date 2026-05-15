#include "wifi_manager.h"

#ifndef NATIVE_TEST

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
        Serial.printf("\n[wifi] Connected -- IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n[wifi] WARN: initial connect failed -- maintain() will retry");
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
// Native test stubs -- no WiFi hardware
void WifiManager::begin() {}
void WifiManager::maintain() {}
bool WifiManager::isConnected() const { return true; }
#endif

#include "EdgeNode.h"
#include <Arduino.h>

void EdgeNode::begin() {
    Serial.begin(115200);
    while (!Serial) delay(10);
    Serial.println("\n[edge] Edge AI Industrial -- starting...");

    _startMs = millis();

    _wifi.begin();

    _mqtt.begin([](const char* topic, const char* payload) {
        Serial.printf("[mqtt] received -- topic: %s  payload: %s\n", topic, payload);
        // Remote config handling: parse payload and apply settings as needed.
        // (Extended in D5 -- A5 backlog item)
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

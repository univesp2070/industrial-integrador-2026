#pragma once
#include "sensor_manager.h"
#include "inference_engine.h"
#include "wifi_manager.h"
#include "mqtt_client.h"

class EdgeNode {
public:
    void begin();
    void loop();

private:
    WifiManager     _wifi;
    MqttClient      _mqtt;
    SensorManager   _sensors;
    InferenceEngine _inference;

    unsigned long _lastPublishMs = 0;
    unsigned long _lastStatusMs  = 0;
    unsigned long _startMs       = 0;
};

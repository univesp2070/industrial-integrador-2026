#pragma once

#if defined(NATIVE_TEST)
#include "../config/device_config.h"
#else
#include "device_config.h"
#endif

class InferenceEngine {
public:
    void           begin();
    InferenceResult run(const SensorReading& r);
};

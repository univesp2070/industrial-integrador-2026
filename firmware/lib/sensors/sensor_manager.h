#pragma once
// Allow both PlatformIO lib-path resolution and direct-include in native tests
#if defined(NATIVE_TEST)
#  include "../config/device_config.h"
#else
#  include "device_config.h"
#endif

class SensorManager {
public:
    void         begin();
    SensorReading read(unsigned long uptime_s);
};

# Design: Firmware Modular ESP32 — D3 Tech Lead

**Data:** 2026-04-04  
**Autor:** Líder Técnico  
**Branch:** `feature/esp32-edge-network-sim-bootstrap`  
**Referência:** `docs/CRONOGRAMA_LIDER_TECNICO_D1_D10.md` (D3), `docs/EDGE_NETWORK_ESP32_ACTION_PLAN.md`

---

## Objetivo

Implementar a base modular do firmware ESP32 em C++ (PlatformIO) com:

- Arquitetura `EdgeNode` orquestradora
- Módulos independentes: `config`, `wifi_manager`, `mqtt_client`, `sensor_manager`, `inference_engine`
- Suporte a `SIMULATION_MODE` via flag de build
- Integração TFLite Micro com modelo placeholder
- Contrato MQTT v1 completo (JSON, LWT, QoS 1, reconnect com backoff)

Critério de aceite: `pio run -e esp32` e `pio run -e esp32_sim` compilam sem erro. Loop lógico padronizado em `EdgeNode`.

---

## Arquitetura

### Estrutura de arquivos

```
firmware/
├── lib/
│   ├── config/
│   │   ├── device_config.h      # constantes, structs SensorReading e InferenceResult
│   │   └── device_config.cpp
│   ├── communication/
│   │   ├── wifi_manager.h/.cpp  # WiFi com reconexão automática
│   │   └── mqtt_client.h/.cpp   # PubSubClient wrapper, publish, LWT, backoff
│   ├── sensors/
│   │   └── sensor_manager.h/.cpp # leitura real ou SIMULATION_MODE
│   └── inference/
│       ├── inference_engine.h/.cpp # TFLite Micro, modelo embarcado
│       └── model_data.h            # array C do modelo .tflite (placeholder)
└── src/
    ├── EdgeNode.h/.cpp           # orquestradora: begin() + loop()
    └── main.cpp                  # 5 linhas: instancia EdgeNode, delega setup/loop
```

### Padrão arquitetural

`EdgeNode` é a única classe que conhece todos os módulos. Cada módulo em `lib/` desconhece os demais — comunicação passa exclusivamente pelos tipos definidos em `device_config.h` (`SensorReading`, `InferenceResult`).

---

## Módulos

### `device_config.h`

Centraliza todas as constantes e os tipos de dados compartilhados:

```cpp
// Configuração de rede e dispositivo
#define DEVICE_ID          "esp32-001"
#define WIFI_SSID          "ssid"
#define WIFI_PASSWORD      "password"
#define MQTT_BROKER        "192.168.1.100"
#define MQTT_PORT          1883
#define MQTT_USER          "edge"
#define MQTT_PASSWORD      "edge_pass"
#define FIRMWARE_VERSION   "1.0.0"

// Intervalos
#define PUBLISH_INTERVAL_MS  5000
#define STATUS_INTERVAL_MS   30000
#define ANOMALY_INTERVAL_S   60   // injeta anomalia a cada N segundos (SIMULATION_MODE)

// Threshold de alerta
#define ANOMALY_THRESHOLD    0.8f

// Tipos de dados entre módulos
struct SensorReading {
    float temperature;  // °C
    float vibration;    // mm/s
    float current;      // A
    unsigned long timestamp_ms;
};

struct InferenceResult {
    char classification[16];  // "normal" ou "anomaly"
    float anomaly_score;       // 0.0 a 1.0
    char model_version[16];
};
```

### `wifi_manager`

- `begin()`: conecta ao WiFi, aguarda com timeout de 10s
- `maintain()`: verifica conexão a cada ciclo, reconecta se desconectado
- `isConnected()`: retorna estado atual
- Não usa `delay()` longo — controle por `millis()`

### Timestamp

- **SIMULATION_MODE:** sem RTC físico. `mqtt_client` sincroniza via NTP (`pool.ntp.org`) após conexão WiFi. Se NTP falhar, usa epoch fixo `2026-01-01T00:00:00Z` + `millis()/1000` como fallback. Formato ISO-8601 UTC gerado por `strftime`.
- **Modo real:** mesma lógica NTP; com RTC externo (DS3231) pode ser adicionado sem mudar a interface.

### `mqtt_client`

- `begin()`: configura LWT (`device/status/{id}` com payload `offline`, retain true, QoS 1)
- `connect()`: conecta ao broker com credenciais
- `maintain()`: chama `loop()` do PubSubClient; se desconectado, aplica backoff (1s→2s→4s→máx 30s) via `millis()`
- `publishSensorData(SensorReading&, InferenceResult&)`: monta JSON v1, publica em `sensor/data/{device_id}` QoS 1
- `publishStatus()`: publica JSON de status em `device/status/{device_id}` QoS 1
- `subscribe(topic, callback)`: assina `device/config/{device_id}` para receber comandos remotos
- Dependência: `ArduinoJson` (já disponível no PlatformIO registry)

### `sensor_manager`

Controlado pela macro `SIMULATION_MODE`:

**Modo simulação:**
- Temperatura: senoidal entre 20°C e 85°C com período de 120s
- Vibração: ruído gaussiano em torno de 0.3 mm/s com picos a cada `ANOMALY_INTERVAL_S`
- Corrente: variação linear entre 2A e 5A
- Anomalia controlada: quando `uptime % ANOMALY_INTERVAL_S == 0`, gera pico de vibração que dispara threshold

**Modo hardware real:**
- Temperatura: DS18B20 via OneWire ou BME280 via I2C
- Vibração: ADXL345 ou MPU6050 via I2C
- Corrente: ACS712 ou INA219 via I2C/ADC
- Interface idêntica ao modo simulação — `EdgeNode` não distingue

### `inference_engine`

- `begin()`: carrega modelo de `model_data.h` (array C) no TFLite Micro interpreter
- `run(SensorReading&)` → `InferenceResult`: normaliza features, executa inferência, retorna classificação e score
- **SIMULATION_MODE**: modelo placeholder calcula `anomaly_score = vibration / 2.0` (score proporcional à vibração)
- **Modo real**: `EloquentTinyML` ou `tflite-micro` do PlatformIO registry; `model_data.h` será substituído pelo modelo treinado
- `model_version`: lido de constante em `model_data.h`

### `EdgeNode`

```cpp
class EdgeNode {
public:
    void begin();   // inicializa todos os módulos na ordem correta
    void loop();    // ciclo principal não-bloqueante
private:
    WifiManager   _wifi;
    MqttClient    _mqtt;
    SensorManager _sensors;
    InferenceEngine _inference;
    unsigned long _lastPublish;
    unsigned long _lastStatus;
};
```

**`begin()` — ordem de inicialização:**
1. `Serial.begin(115200)`
2. `_wifi.begin()`
3. `_mqtt.begin()` (configura LWT antes de conectar)
4. `_mqtt.connect()`
5. `_sensors.begin()`
6. `_inference.begin()`
7. `_mqtt.publishStatus()` (publica `online` na inicialização)

**`loop()` — ciclo principal:**
1. `_wifi.maintain()`
2. `_mqtt.maintain()`
3. Se `millis() - _lastPublish >= PUBLISH_INTERVAL_MS`:
   - `SensorReading r = _sensors.read()`
   - `InferenceResult inf = _inference.run(r)`
   - `_mqtt.publishSensorData(r, inf)`
   - `_lastPublish = millis()`
4. Se `millis() - _lastStatus >= STATUS_INTERVAL_MS`:
   - `_mqtt.publishStatus()`
   - `_lastStatus = millis()`

---

## Contrato MQTT v1

### Tópico `sensor/data/{device_id}` (QoS 1)

```json
{
  "device_id": "esp32-001",
  "timestamp": "2026-04-04T10:30:00Z",
  "sensors": {
    "temperature": { "value": 72.5, "unit": "C" },
    "vibration":   { "value": 0.45, "unit": "mm_s" },
    "current":     { "value": 3.2,  "unit": "A" }
  },
  "inference": {
    "classification": "normal",
    "anomaly_score": 0.12,
    "model_version": "v1.0"
  }
}
```

### Tópico `device/status/{device_id}` (QoS 1)

```json
{
  "device_id": "esp32-001",
  "status": "online",
  "firmware_version": "1.0.0",
  "uptime_seconds": 3600,
  "free_memory": 45000,
  "wifi_rssi": -42,
  "timestamp": "2026-04-04T10:30:00Z"
}
```

### Last Will Testament

- Tópico: `device/status/{device_id}`
- Payload: `{"device_id":"esp32-001","status":"offline"}`
- QoS 1, retain: true

---

## Configuração PlatformIO

```ini
[env:esp32]
platform = espressif32
board = esp32dev
framework = arduino
lib_deps =
    knolleary/PubSubClient@^2.8
    bblanchon/ArduinoJson@^7.0
    milesburton/DallasTemperature@^3.11
    paulstoffregen/OneWire@^2.3
    bolderflight/bolder-flight-systems-mpu6050@^1.0
    wollewald/INA219_WE@^1.3
    eloquentarduino/EloquentTinyML@^0.0.9
build_flags = -D FIRMWARE_VERSION='"1.0.0"'

[env:esp32_sim]
platform = espressif32
board = esp32dev
framework = arduino
lib_deps =
    knolleary/PubSubClient@^2.8
    bblanchon/ArduinoJson@^7.0
    eloquentarduino/EloquentTinyML@^0.0.9
build_flags =
    -D SIMULATION_MODE
    -D FIRMWARE_VERSION='"sim-1.0.0"'
```

---

## Critérios de aceite (D3)

- [ ] `pio run -e esp32` compila sem erro
- [ ] `pio run -e esp32_sim` compila sem erro
- [ ] `main.cpp` sem TODOs — delega tudo para `EdgeNode`
- [ ] Loop principal não usa `delay()` para esperas longas (usa `millis()`)
- [ ] JSON publicado é compatível com contrato v1 (validável via `--dry-run` do simulador Python)
- [ ] LWT configurado antes de qualquer `connect()`

---

## Fora de escopo (D3)

- OTA update
- TLS/SSL no MQTT
- Modelo TFLite treinado (placeholder é suficiente)
- Drivers de sensor físico validados em hardware (só compila, sem teste em bancada)
- Integração com backend (D4)

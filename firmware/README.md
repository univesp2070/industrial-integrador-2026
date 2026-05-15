# Firmware - Edge Layer (ESP32/STM32)

Módulo responsável pelo firmware embarcado que roda nos microcontroladores ESP32/STM32.

## Responsabilidades

- Leitura de sensores (I2C, SPI, GPIO)
- Inferência local com TensorFlow Lite Micro
- Classificação e detecção de anomalias
- Comunicação MQTT + TLS com o broker
- Envio apenas de dados processados (payload reduzido)

## Tecnologias

- C/C++
- PlatformIO
- TensorFlow Lite Micro
- FreeRTOS
- MQTT Client (PubSubClient / ESP-MQTT)

## Estrutura

```
firmware/
├── src/
│   ├── main.cpp              # Entry point
│   ├── sensors/              # Drivers de sensores
│   ├── inference/            # Motor de inferência TFLite
│   ├── communication/        # MQTT client
│   └── config/               # Configurações do dispositivo
├── lib/                      # Bibliotecas customizadas
├── models/                   # Modelos .tflite
├── test/                     # Testes unitários
├── include/                  # Headers globais
└── platformio.ini            # Configuração PlatformIO
```

## Build & Flash

```bash
# Build
pio run

# Upload para o dispositivo
pio run --target upload

# Monitor serial
pio device monitor
```

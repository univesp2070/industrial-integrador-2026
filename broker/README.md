# MQTT Broker - EMQX

Módulo de configuração do broker MQTT (EMQX) para comunicação IoT.

## Responsabilidades

- Receber mensagens dos dispositivos IoT
- Gerenciamento de tópicos MQTT
- Autenticação por certificado
- Escalabilidade horizontal

## Tópicos MQTT

| Tópico | Direção | Descrição |
|--------|---------|-----------|
| `sensor/data/{device_id}` | Device → Cloud | Dados processados do sensor |
| `device/status/{device_id}` | Device → Cloud | Status do dispositivo |
| `device/config/{device_id}` | Cloud → Device | Configuração remota |
| `device/ota/{device_id}` | Cloud → Device | Atualização OTA |

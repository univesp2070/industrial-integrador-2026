# Event Streaming - Apache Kafka

Módulo responsável pelo processamento assíncrono de eventos via Apache Kafka.

## Responsabilidades

- Processamento assíncrono de dados dos sensores
- Desacoplamento entre produtor (Backend API) e consumidores
- Garantia de entrega de mensagens
- Replay de eventos

## Tópicos Kafka

| Tópico | Descrição |
|--------|-----------|
| `sensor.data.raw` | Dados brutos dos sensores |
| `sensor.data.processed` | Dados processados após inferência |
| `alerts.triggered` | Alertas gerados pelo sistema |
| `device.status` | Status dos dispositivos |

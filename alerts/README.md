# Sistema de Alertas

Serviço de notificações e alertas em tempo real.

## Responsabilidades

- Web Push notifications
- Envio de emails
- Notificações em tempo real via WebSocket
- Integração com sistemas externos (webhooks)

## Tipos de Alerta

| Tipo | Severidade | Descrição |
|------|-----------|-----------|
| `anomaly_detected` | HIGH | Anomalia detectada pelo motor de inferência |
| `device_offline` | MEDIUM | Dispositivo ficou offline |
| `threshold_exceeded` | HIGH | Valor do sensor excedeu limite |
| `maintenance_required` | LOW | Manutenção preventiva necessária |

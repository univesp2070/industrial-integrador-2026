# Backlog Específico — Codificação e Features

Data: 2026-04-02  
Foco: apenas tarefas de implementação técnica (código), sem atividades de gestão.

## Objetivo Técnico

Entregar, por código, o fluxo funcional:

`Edge (ESP32/simulador) -> MQTT (EMQX) -> Backend -> PostgreSQL/TimescaleDB -> API`

## Prioridade de Entrega

1. `P0` Bloqueante para integração ponta-a-ponta
2. `P1` Necessário para operação estável
3. `P2` Evolução/polimento

## EPIC A — Firmware / Edge Runtime

### A1. Estrutura modular base do firmware (`P0`)

- [ ] Criar módulos:
  - `firmware/lib/config/device_config.h/.cpp`
  - `firmware/lib/communication/wifi_manager.h/.cpp`
  - `firmware/lib/communication/mqtt_client.h/.cpp`
  - `firmware/lib/sensors/sensor_manager.h/.cpp`
  - `firmware/lib/inference/inference_engine.h/.cpp`
- [ ] Atualizar `firmware/src/main.cpp` para usar os módulos.

Aceite técnico:

- Build `pio run -e esp32` sem erro.
- `main.cpp` sem TODOs críticos no fluxo principal.

### A2. Publicação MQTT de dados processados (`P0`)

- [ ] Implementar publicação em:
  - `sensor/data/{device_id}`
  - `device/status/{device_id}`
- [ ] Garantir JSON compatível com contrato `v1`.

Aceite técnico:

- Mensagens válidas recebidas no EMQX.
- Campos obrigatórios presentes (`device_id`, `timestamp`, `inference` etc.).

### A3. Simulação de sensores no firmware (`P0`)

- [ ] Implementar modo `SIMULATION` para rodar sem sensor físico.
- [ ] Gerar leitura sintética para temperatura, vibração e corrente.
- [ ] Injetar anomalia controlada (threshold testável).

Aceite técnico:

- Dados variam ao longo do tempo.
- Existe geração previsível de eventos anômalos.

### A4. Reconnect e resiliência MQTT/Wi-Fi (`P1`)

- [ ] Auto-reconexão Wi-Fi.
- [ ] Auto-reconexão MQTT com backoff.
- [ ] Last-will status offline.

Aceite técnico:

- Reiniciar broker não trava o loop.
- Dispositivo volta a publicar após reconexão.

### A5. Consumo de comandos remotos (`P1`)

- [ ] Assinar `device/config/{device_id}`.
- [ ] Aplicar atualização de parâmetros (ex.: intervalo de coleta).

Aceite técnico:

- Mudança de configuração refletida em runtime sem reflashing.

## EPIC B — Network / Broker / Streaming

### B1. Config EMQX mínima de segurança e tópicos (`P0`)

- [ ] Criar configuração inicial em `broker/config/`:
  - auth básica (`username/password`) para dev
  - ACL para publish/subscribe por tópico

Aceite técnico:

- Cliente não autorizado não publica tópicos protegidos.

### B2. Definição de tópicos Kafka (`P1`)

- [ ] Criar bootstrap/config em `streaming/config/`:
  - `sensor.data.raw`
  - `sensor.data.processed`
  - `alerts.triggered`
  - `device.status`

Aceite técnico:

- Tópicos criados no ambiente local e usados pelo backend.

## EPIC C — Backend Ingestion + API

### C1. Modelos + Repositórios JPA (`P0`)

- [ ] Implementar entidades:
  - `Device`, `SensorData`, `Alert`, `User`
- [ ] Implementar repositories com queries base.

Aceite técnico:

- Aplicação sobe com `ddl-auto=validate`.
- Queries básicas funcionando.

### C2. Ingestão MQTT (`P0`)

- [ ] Implementar `MqttMessageHandler` para:
  - `sensor/data/+`
  - `device/status/+`
- [ ] Validar e desserializar JSON.

Aceite técnico:

- Backend consome payload do simulador sem erro de parsing.

### C3. Persistência em `devices` e `sensor_data` (`P0`)

- [ ] Upsert de dispositivo via status/data.
- [ ] Inserir 1 linha por métrica no `sensor_data`.
- [ ] Persistir contexto em `metadata` JSONB.

Aceite técnico:

- Para 1 mensagem com 3 sensores => 3 linhas em `sensor_data`.

### C4. Regra de alerta por anomalia (`P0`)

- [ ] Criar alerta quando `anomaly_score >= threshold`.
- [ ] Definir threshold inicial por config.

Aceite técnico:

- Evento anômalo gera linha em `alerts`.

### C5. Endpoints mínimos para validação (`P1`)

- [ ] `GET /api/devices`
- [ ] `GET /api/sensors/latest/{deviceId}`
- [ ] `GET /api/sensors/data?deviceId=&start=&end=`
- [ ] `GET /api/alerts?acknowledged=false`

Aceite técnico:

- Endpoints retornam dados reais da ingestão.

## EPIC D — Frontend (consumo de dados reais)

### D1. Camada de API e tipos (`P1`)

- [ ] Criar `types` e `services` alinhados ao backend.
- [ ] Implementar autenticação básica com token.

Aceite técnico:

- Requests autenticados consumindo endpoints do backend.

### D2. Dashboard e telas operacionais (`P1`)

- [ ] Dashboard com KPIs de devices/alertas.
- [ ] Tela de dispositivos com status e última leitura.
- [ ] Tela de alertas com reconhecimento.

Aceite técnico:

- Frontend renderiza dados reais sem mock no fluxo principal.

## EPIC E — Testes Técnicos

### E1. Testes de contrato (payload) (`P0`)

- [ ] Validar schema do payload no simulador e no backend.

Aceite técnico:

- Payload inválido é rejeitado com log claro.

### E2. Teste E2E local (`P0`)

- [ ] Cenário:
  - simulador publica
  - backend consome
  - banco persiste
  - API retorna dados

Aceite técnico:

- Fluxo completo passando em ambiente local.

### E3. Soak test 1h (`P1`)

- [ ] Rodar carga contínua de 1 hora.
- [ ] Verificar estabilidade e reconexão.

Aceite técnico:

- Sem falha crítica ou perda sistêmica de ingestão.

## Ordem Recomendada de PRs (somente codificação)

1. PR-1: `A1 + A2` (base firmware + publish MQTT)
2. PR-2: `C1 + C2` (modelos/repo + ingestão MQTT)
3. PR-3: `C3 + C4` (persistência + alerta)
4. PR-4: `C5 + D1` (endpoints + cliente frontend)
5. PR-5: `D2 + E2` (UI com dados reais + validação E2E)
6. PR-6: `A4 + E3` (resiliência + soak test)

## Definição de Pronto (DoD) — Feature de Código

Uma feature só fecha quando:

1. Compila/builda no módulo correspondente.
2. Tem teste mínimo (unitário ou integração) para o comportamento crítico.
3. Está integrada ao contrato definido.
4. Foi validada no fluxo local (quando aplicável).
5. Está documentada em README/arquivo técnico do módulo.

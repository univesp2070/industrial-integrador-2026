# Plano de Ação — Edge AI Industrial

**Data:** 08/03/2026  
**Equipe:** 4 desenvolvedores + 1 líder técnico (firmware/integração)

---

## Distribuição da Equipe

| Pessoa | Área | Foco Principal |
|--------|------|----------------|
| **Dev Backend 1** | Backend | Models, Repositories, Security (Auth/JWT) |
| **Dev Backend 2** | Backend | Controllers, Services, MQTT/Kafka integration |
| **Dev Frontend 1** | Frontend | Layout, páginas (App Router), componentes visuais |
| **Dev Frontend 2** | Frontend | Services (API client), hooks, tipos TypeScript, gráficos |
| **Líder Técnico (você)** | Firmware + Integração | ESP32, sensores, MQTT client, modelo TFLite, integração ponta a ponta |

---

## Estado Atual do Projeto

| Módulo | Status |
|--------|--------|
| Infraestrutura (Docker Compose) | ✅ Completo — PostgreSQL+TimescaleDB, EMQX, Kafka, Redis |
| Database Schema | ✅ Completo — 8 tabelas, hypertable, índices |
| CI/CD Pipelines | ✅ Completo — GitHub Actions para backend e frontend |
| Makefile | ✅ Completo — comandos para todos os módulos |
| Backend (config/dependências) | ✅ Completo — Spring Boot 3.3, Java 21, todas as libs |
| Backend (código) | ❌ Vazio — todos os pacotes só têm .gitkeep |
| Frontend (config/dependências) | ✅ Completo — Next.js 15, React 19, Recharts, Tailwind |
| Frontend (código) | ❌ Vazio — todos os diretórios só têm .gitkeep |
| Firmware (config PlatformIO) | ✅ Completo — ESP32 + STM32 configurados |
| Firmware (código) | ❌ Vazio — main.cpp só tem TODOs |
| Broker/Streaming config | ❌ Vazio |
| Alerts | ❌ Vazio |

---

## BACKEND — Tarefas Detalhadas

### Dev Backend 1: Models, Repositories e Security

#### Sprint 1 — Fundação (Prioridade ALTA)

**1. Entidades JPA (`model/`)**

Criar as entidades mapeando o schema SQL já existente em `database/migrations/V001__initial_schema.sql`:

| Arquivo | Tabela SQL | Campos Principais |
|---------|-----------|-------------------|
| `Device.java` | `devices` | id (UUID), name, deviceType, firmwareVersion, location, status, lastSeenAt |
| `SensorData.java` | `sensor_data` | time, deviceId, sensorType, value, unit, classification, anomalyScore, metadata (JSONB) |
| `User.java` | `users` | id (UUID), email, passwordHash, name, role (ENUM: VIEWER, OPERATOR, ADMIN), active |
| `Alert.java` | `alerts` | id, deviceId, alertType, severity (ENUM), message, acknowledged, acknowledgedBy, acknowledgedAt |

DTOs a criar:
| Arquivo | Uso |
|---------|-----|
| `DeviceDTO.java` | Resposta da API para dispositivos |
| `SensorDataDTO.java` | Resposta da API para dados de sensores |
| `AlertDTO.java` | Resposta da API para alertas |
| `UserDTO.java` | Resposta da API para usuários (sem passwordHash!) |
| `LoginRequest.java` | Request body para login |
| `LoginResponse.java` | Response com JWT token |
| `RegisterRequest.java` | Request body para registro |

**2. Repositories (`repository/`)**

| Arquivo | Métodos Customizados |
|---------|---------------------|
| `DeviceRepository.java` | `findByStatus()`, `findByDeviceType()`, `findByLocation()` |
| `SensorDataRepository.java` | `findByDeviceIdAndTimeBetween()`, `findLatestByDeviceId()` |
| `UserRepository.java` | `findByEmail()`, `existsByEmail()` |
| `AlertRepository.java` | `findByDeviceId()`, `findByAcknowledgedFalse()`, `findBySeverity()` |

**3. Security (`security/`)**

| Arquivo | Responsabilidade |
|---------|-----------------|
| `JwtTokenProvider.java` | Gerar e validar tokens JWT (usar JJWT 0.12.5 já no build.gradle) |
| `JwtAuthenticationFilter.java` | Filtro Spring Security — intercepta requests, valida token no header `Authorization: Bearer <token>` |
| `SecurityConfig.java` | Configuração do SecurityFilterChain — endpoints públicos (`/api/auth/**`), protegidos (`/api/**`), CORS |
| `UserDetailsServiceImpl.java` | Implementação de `UserDetailsService` — carrega user do banco |
| `AuthController.java` | Endpoints: `POST /api/auth/login`, `POST /api/auth/register` |

> **Referência:** As configs de JWT (secret, expiração) já estão no `application.yml`

---

### Dev Backend 2: Controllers, Services e Integrações

#### Sprint 1 — Fundação (Prioridade ALTA)

**1. Configurações (`config/`)**

| Arquivo | Responsabilidade |
|---------|-----------------|
| `CorsConfig.java` | Liberar CORS para o frontend (localhost:3000 em dev) |
| `WebSocketConfig.java` | Configurar STOMP WebSocket em `/ws` para real-time no frontend |
| `MqttConfig.java` | Configurar conexão com EMQX (host/porta já no application.yml) |
| `KafkaConfig.java` | Configurar tópicos Kafka: `sensor.data.raw`, `sensor.data.processed`, `alerts.triggered`, `device.status` |

**2. Services (`service/`)**

| Arquivo | Responsabilidade |
|---------|-----------------|
| `DeviceService.java` | CRUD de devices, atualizar status, `updateLastSeen()` |
| `SensorDataService.java` | Salvar dados de sensores, consultas por período, agregações |
| `AlertService.java` | Criar alertas, listar, marcar como acknowledged |
| `UserService.java` | Registro de usuário (hash senha com BCrypt), buscar perfil |
| `DashboardService.java` | Dados agregados para o dashboard: contagem devices, últimas leituras, alertas ativos |

**3. Controllers (`controller/`)**

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `GET /api/devices` | `DeviceController` | Listar todos os dispositivos |
| `GET /api/devices/{id}` | `DeviceController` | Detalhes de um dispositivo |
| `POST /api/devices` | `DeviceController` | Registrar novo dispositivo |
| `PUT /api/devices/{id}` | `DeviceController` | Atualizar dispositivo |
| `GET /api/sensors/data` | `SensorDataController` | Dados por período (query params: deviceId, start, end) |
| `GET /api/sensors/latest/{deviceId}` | `SensorDataController` | Última leitura |
| `GET /api/alerts` | `AlertController` | Listar alertas (filtros: severity, acknowledged) |
| `PUT /api/alerts/{id}/acknowledge` | `AlertController` | Marcar alerta como reconhecido |
| `GET /api/dashboard/summary` | `DashboardController` | Resumo geral para o dashboard |

**4. Integrações MQTT/Kafka (`mqtt/`, `kafka/`)**

| Arquivo | Responsabilidade |
|---------|-----------------|
| `MqttMessageHandler.java` | Receber mensagens dos tópicos `sensor/data/+` e `device/status/+`, parsear JSON, publicar no Kafka |
| `KafkaProducerService.java` | Produzir mensagens nos tópicos Kafka |
| `KafkaConsumerService.java` | Consumir do `sensor.data.raw`, salvar no banco, disparar alertas se necessário |
| `WebSocketPublisher.java` | Enviar dados em tempo real para o frontend via WebSocket STOMP |

---

## FRONTEND — Tarefas Detalhadas

### Dev Frontend 1: Layout, Páginas e Componentes Visuais

#### Sprint 1 — Fundação (Prioridade ALTA)

**1. Layout Base (`src/app/`)**

| Arquivo | Responsabilidade |
|---------|-----------------|
| `layout.tsx` | Layout raiz — sidebar de navegação, header com user info, tema escuro industrial |
| `page.tsx` | Página inicial — redireciona para `/dashboard` |
| `globals.css` | Estilos globais Tailwind + variáveis CSS do tema |
| `dashboard/page.tsx` | Dashboard principal — grid com cards de KPIs, gráficos, lista de alertas |
| `devices/page.tsx` | Lista de dispositivos — tabela com status, filtros |
| `devices/[id]/page.tsx` | Detalhes do dispositivo — dados em tempo real, histórico |
| `alerts/page.tsx` | Central de alertas — lista com filtros por severidade |
| `settings/page.tsx` | Configurações — perfil do usuário |
| `login/page.tsx` | Página de login (pública, sem sidebar) |

**2. Componentes Visuais (`src/components/`)**

| Componente | Descrição |
|------------|-----------|
| `Sidebar.tsx` | Menu lateral com links: Dashboard, Devices, Alerts, Settings |
| `Header.tsx` | Barra superior com nome do usuário, notificações, logout |
| `DeviceCard.tsx` | Card individual de dispositivo (nome, status, última leitura) |
| `AlertBadge.tsx` | Badge de severidade (critical=vermelho, warning=amarelo, info=azul) |
| `StatusIndicator.tsx` | Bolinha de status (online=verde, offline=vermelho, warning=amarelo) |
| `KpiCard.tsx` | Card de KPI para o dashboard (ícone, valor, label, tendência) |
| `DataTable.tsx` | Tabela genérica reutilizável com paginação e sort |
| `LoadingSpinner.tsx` | Spinner de carregamento |
| `EmptyState.tsx` | Componente para estados vazios |

> **Stack visual:** Tailwind CSS 3.4 (já configurado). Tema escuro com tons de azul/cinza industrial.

---

### Dev Frontend 2: Services, Hooks, Types e Gráficos

#### Sprint 1 — Fundação (Prioridade ALTA)

**1. Types (`src/types/`)**

| Arquivo | Tipos |
|---------|-------|
| `device.ts` | `Device`, `DeviceStatus`, `DeviceType` |
| `sensor.ts` | `SensorData`, `SensorType`, `Classification` |
| `alert.ts` | `Alert`, `AlertSeverity`, `AlertType` |
| `user.ts` | `User`, `UserRole`, `LoginRequest`, `LoginResponse` |
| `dashboard.ts` | `DashboardSummary`, `KpiData` |
| `api.ts` | `ApiResponse<T>`, `PaginatedResponse<T>`, `ApiError` |

**2. Services (`src/services/`)**

| Arquivo | Responsabilidade |
|---------|-----------------|
| `api.ts` | Cliente HTTP base (fetch/axios) — base URL, interceptor de JWT, tratamento de erros |
| `auth.service.ts` | `login()`, `register()`, `logout()`, `getToken()`, `isAuthenticated()` |
| `device.service.ts` | `getDevices()`, `getDevice(id)`, `createDevice()`, `updateDevice()` |
| `sensor.service.ts` | `getSensorData(deviceId, range)`, `getLatest(deviceId)` |
| `alert.service.ts` | `getAlerts(filters)`, `acknowledgeAlert(id)` |
| `dashboard.service.ts` | `getSummary()` |
| `websocket.service.ts` | Conexão WebSocket STOMP — subscribe em canais de real-time |

**3. Hooks (`src/hooks/`)**

| Hook | Uso |
|------|-----|
| `useAuth.ts` | Contexto de autenticação — user, login, logout, isLoading |
| `useDevices.ts` | Fetch + cache de dispositivos |
| `useSensorData.ts` | Fetch dados de sensores com polling/WebSocket |
| `useAlerts.ts` | Fetch alertas + real-time updates |
| `useWebSocket.ts` | Hook genérico para conexões WebSocket |
| `useDashboard.ts` | Dados agregados do dashboard |

**4. Gráficos (usando Recharts já instalado)**

| Componente | Tipo | Uso |
|------------|------|-----|
| `SensorChart.tsx` | LineChart | Histórico de leituras de sensores ao longo do tempo |
| `AnomalyChart.tsx` | AreaChart | Score de anomalia com threshold line |
| `DeviceDistribution.tsx` | PieChart | Distribuição de dispositivos por status |
| `AlertTimeline.tsx` | BarChart | Alertas por dia/hora |

---

## FIRMWARE + INTEGRAÇÃO (Líder Técnico)

### Sprint 1 — Fundação (Prioridade ALTA)

**1. Estrutura de Bibliotecas (`firmware/lib/`)**

| Diretório/Arquivo | Responsabilidade |
|--------------------|-----------------|
| `sensors/sensor_manager.h/.cpp` | Abstração de sensores — leitura I2C/SPI, calibração |
| `sensors/temperature_sensor.h/.cpp` | Driver sensor de temperatura (ex: DS18B20, BME280) |
| `sensors/vibration_sensor.h/.cpp` | Driver sensor de vibração (ex: ADXL345, MPU6050) |
| `sensors/current_sensor.h/.cpp` | Driver sensor de corrente (ex: ACS712, INA219) |
| `communication/mqtt_client.h/.cpp` | Wrapper PubSubClient — connect, publish, subscribe, reconnect automático |
| `communication/wifi_manager.h/.cpp` | Conexão WiFi com reconexão automática |
| `config/device_config.h/.cpp` | Configurações do device (ID, WiFi SSID/pass, MQTT broker, intervalos) |
| `inference/inference_engine.h/.cpp` | Carregar modelo TFLite, rodar inferência, retornar classificação + anomaly_score |

**2. Firmware Principal (`firmware/src/main.cpp`)**

Fluxo do loop principal:
```
setup():
  1. Inicializar Serial (debug)
  2. Conectar WiFi
  3. Conectar MQTT broker (EMQX)
  4. Inicializar sensores
  5. Carregar modelo TFLite
  6. Publicar status "online" em device/status/{device_id}

loop():
  1. Ler sensores (temperatura, vibração, corrente)
  2. Rodar inferência no modelo local
  3. Montar JSON com dados + classificação + anomaly_score
  4. Publicar em sensor/data/{device_id}
  5. Verificar mensagens recebidas (config, OTA)
  6. Delay configurável (ex: 5 segundos)
```

**3. Formato JSON das Mensagens MQTT**

```json
// Tópico: sensor/data/{device_id}
{
  "device_id": "esp32-001",
  "timestamp": "2026-03-08T10:30:00Z",
  "sensors": {
    "temperature": { "value": 72.5, "unit": "°C" },
    "vibration": { "value": 0.45, "unit": "mm/s" },
    "current": { "value": 3.2, "unit": "A" }
  },
  "inference": {
    "classification": "normal",
    "anomaly_score": 0.12,
    "model_version": "v1.0"
  }
}

// Tópico: device/status/{device_id}
{
  "device_id": "esp32-001",
  "status": "online",
  "firmware_version": "1.0.0",
  "uptime_seconds": 3600,
  "free_memory": 45000,
  "wifi_rssi": -42
}
```

**4. Configuração do Broker EMQX (`broker/config/`)**

- Criar arquivo `emqx.conf` com ACL rules para os tópicos
- Configurar autenticação por username/password ou certificado

**5. Configuração Kafka (`streaming/config/`)**

- Criar arquivo com definição dos tópicos e partições
- Configurar retenção de dados

---

## Contrato de Integração (CRÍTICO)

> Todos devem seguir este contrato para que a integração funcione.

### API REST Base URL
```
DEV: http://localhost:8080/api
```

### Autenticação
```
POST /api/auth/login → { email, password } → { token, user }
Header: Authorization: Bearer <jwt_token>
```

### Tópicos MQTT (Firmware ↔ Backend)
```
sensor/data/{device_id}     — Firmware publica, Backend consome
device/status/{device_id}   — Firmware publica, Backend consome
device/config/{device_id}   — Backend publica, Firmware consome
```

### Tópicos Kafka (Backend interno)
```
sensor.data.raw         — MqttHandler produz, Consumer consome
sensor.data.processed   — Consumer produz após processar
alerts.triggered        — AlertService produz
device.status           — MqttHandler produz
```

### WebSocket (Backend → Frontend)
```
Endpoint: ws://localhost:8080/ws
Canal: /topic/sensors/{deviceId}   — dados em tempo real
Canal: /topic/alerts               — alertas em tempo real
Canal: /topic/devices/status       — mudanças de status
```

---

## Ordem de Execução Recomendada

### Fase 1 — Base (Semana 1)
```
PARALELO:
├── Backend 1: Models + Repositories + Security
├── Backend 2: Configs (CORS, WebSocket) + DeviceService + DeviceController
├── Frontend 1: Layout + Login page + Dashboard page (mockado)
├── Frontend 2: Types + API client + AuthService
└── Líder: Firmware WiFi + MQTT client + leitura de 1 sensor
```

### Fase 2 — Integração (Semana 2)
```
PARALELO:
├── Backend 1: Polir Security + Testes unitários
├── Backend 2: MQTT Handler + Kafka + SensorDataService + AlertService
├── Frontend 1: Devices page + Alerts page + componentes visuais
├── Frontend 2: DeviceService + SensorService + hooks + gráficos Recharts
└── Líder: Inference engine + JSON completo + testar fluxo MQTT→Backend
```

### Fase 3 — Real-time + Polish (Semana 3)
```
PARALELO:
├── Backend 1+2: WebSocket publisher + Dashboard endpoint + testes
├── Frontend 1+2: WebSocket real-time + gráficos ao vivo + responsividade
└── Líder: Integração ponta a ponta + OTA + testes E2E
```

---

## Como Rodar o Ambiente Local

```bash
# 1. Subir infraestrutura (PostgreSQL, EMQX, Kafka, Redis)
make up

# 2. Backend (em outro terminal)
make backend-run

# 3. Frontend (em outro terminal)
make frontend-dev

# 4. Firmware (se tiver ESP32 conectado)
make firmware-build
make firmware-upload
make firmware-monitor

# Parar tudo
make down

# Dashboard EMQX (ver dispositivos MQTT)
# http://localhost:18083 (admin/public)
```

---

## Regras de Git (Git Flow)

| Branch | Uso |
|--------|-----|
| `main` | Produção — só merge de release |
| `develop` | Branch principal de desenvolvimento |
| `feature/backend-models` | Exemplo: feature do Backend 1 |
| `feature/frontend-layout` | Exemplo: feature do Frontend 1 |
| `feature/firmware-sensors` | Exemplo: feature do Firmware |

**Fluxo:**
1. Criar branch `feature/xxx` a partir de `develop`
2. Desenvolver e commitar
3. Abrir PR para `develop`
4. Code review (pelo menos 1 aprovação)
5. Merge squash para `develop`

**Convenção de commits:**
```
feat(backend): add Device entity and repository
feat(frontend): create dashboard layout
fix(firmware): fix MQTT reconnection logic
docs: update API documentation
```

---

## Checklist de Validação por Fase

### Fase 1 ✅ Critérios de Aceite
- [ ] Backend compila e roda (`make backend-run`)
- [ ] Login funciona e retorna JWT
- [ ] `GET /api/devices` retorna lista (mesmo vazia)
- [ ] Frontend roda (`make frontend-dev`)
- [ ] Tela de login aparece e funciona
- [ ] Dashboard renderiza (dados mockados OK)
- [ ] Firmware conecta no WiFi e no EMQX
- [ ] Firmware publica JSON no tópico MQTT

### Fase 2 ✅ Critérios de Aceite
- [ ] Dados do firmware chegam no banco (via MQTT → Kafka → Service)
- [ ] `GET /api/sensors/data` retorna dados reais
- [ ] Frontend lista dispositivos e alertas do backend
- [ ] Gráficos Recharts renderizam dados reais
- [ ] Alertas são criados automaticamente quando anomaly_score > threshold

### Fase 3 ✅ Critérios de Aceite
- [ ] Dashboard atualiza em tempo real via WebSocket
- [ ] Fluxo completo: Sensor → ESP32 → MQTT → Kafka → DB → API → Frontend
- [ ] Reconhecer alertas pelo frontend
- [ ] Sistema roda estável por 1 hora sem erros

# Edge AI Industrial — Arquitetura do Sistema

Projeto de monitoramento industrial com inteligência artificial embarcada no edge,
desenvolvido para o Projeto Integrador 5 da UNIVESP (prazo: junho/2026).

---

## Visão Geral

O sistema coleta leituras de sensores industriais (temperatura, vibração, corrente elétrica)
via ESP32, executa inferência local de anomalias com TFLite Micro, e transmite os dados
por MQTT para um backend Spring Boot que os persiste no TimescaleDB via Kafka.
Um dashboard Next.js exibe gráficos em tempo real e uma tabela de anomalias.

```
ESP32 (firmware/simulador)
    │  MQTT  sensor/data/#  device/status/#
    ▼
EMQX Broker (porta 1883)
    │  Spring Integration MQTT
    ▼
Spring Boot Backend (porta 8082)
    │  Kafka Producer
    ▼
Apache Kafka — tópico sensor-readings (porta 9092)
    │  Kafka Consumer
    ▼
TimescaleDB / PostgreSQL (porta 5433)
    │  REST API com JWT
    ▼
Next.js Dashboard (porta 3000)
```

---

## Componentes e Tecnologias

### Firmware — `firmware/`

| Item | Detalhe |
|------|---------|
| Hardware | ESP32 (plataforma PlatformIO) |
| Linguagem | C++17 modular |
| Módulos | `SensorManager`, `InferenceEngine`, `MqttClient`, `WifiManager`, `EdgeNode` |
| Inferência | TFLite Micro (modelo treinado com scikit-learn + tflite-micro) |
| Simulador | `firmware/simulator/esp32_sensor_simulator.py` — replica o ESP32 em Python via paho-mqtt |
| Seed histórico | `firmware/simulator/seed_historical.py` — popula 2 dias de dados sintéticos no banco |

**Tópicos MQTT publicados:**
- `sensor/data/{device_id}` — payload com temperatura, vibração, corrente e inferência
- `device/status/{device_id}` — heartbeat do dispositivo (online/offline)

### Broker MQTT — EMQX 5.6

| Item | Detalhe |
|------|---------|
| Container | `edgeai-emqx` |
| Porta MQTT | 1883 |
| Dashboard admin | http://localhost:18083 |
| Autenticação | sem autenticação (desenvolvimento) |

### Backend — `backend/`

| Item | Detalhe |
|------|---------|
| Framework | Spring Boot 3.3 + Java 21 |
| Porta | 8082 |
| Segurança | Spring Security 6 — JWT stateless (JJWT 0.12.5) |
| MQTT | Spring Integration MQTT — subscribe em `sensor/data/#` e `device/status/#` |
| Kafka | Spring Kafka 3 — producer no subscriber MQTT, consumer persiste no banco |
| Banco | Spring Data JPA (entidades `Device`, `User`) + JdbcTemplate (`sensor_data`) |
| Migrations | SQL manual em `database/migrations/` montado no `initdb.d` do container |

**Endpoints REST:**

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/login` | Retorna JWT (email + senha) |
| GET | `/api/devices` | Lista dispositivos cadastrados |
| GET | `/api/sensors/latest` | Última leitura por dispositivo |
| GET | `/api/sensors/recent?minutes=60` | Leituras da última N minutos (todos os dispositivos e tipos) |
| GET | `/api/sensors/readings?deviceId=&from=&to=` | Leituras por dispositivo e intervalo |
| GET | `/api/sensors/anomalies` | Últimas 100 anomalias detectadas |
| GET | `/actuator/health` | Health check |

**Estrutura de pacotes:**
```
com.edgeai.industrial
├── domain/          Device, User  (JPA entities)
├── dto/             SensorPayloadDto, SensorReadingDto, DeviceStatusDto
├── repository/      DeviceRepository, UserRepository, SensorDataRepository
├── service/         DeviceService, SensorService
├── mqtt/            MqttConfig, MqttSubscriber
├── kafka/           KafkaConfig, SensorProducer, SensorConsumer
├── controller/      DeviceController, SensorController, AuthController
└── security/        JwtService, JwtFilter, UserDetailsServiceImpl, SecurityConfig
```

### Banco de Dados — TimescaleDB (PostgreSQL 16)

| Item | Detalhe |
|------|---------|
| Container | `edgeai-postgres` |
| Porta | **5433** (5432 ocupada pelo PostgreSQL 17 nativo do Windows) |
| Extensão | TimescaleDB — `sensor_data` é uma hypertable particionada por `time` |
| Credenciais | usuário `edgeai`, senha `edgeai`, banco `edgeai` |

**Tabelas principais:**

| Tabela | Descrição |
|--------|-----------|
| `devices` | Dispositivos ESP32 registrados |
| `users` | Usuários do sistema (auth JWT) |
| `sensor_data` | Hypertable TimescaleDB — temperatura, vibração, corrente |
| `alerts` | Alertas (schema criado, não utilizado na versão atual) |

**Usuário admin padrão:**
- Email: `admin@edgeai.local`
- Senha: `admin123`

### Kafka — Apache Kafka 3.7 (KRaft, sem Zookeeper)

| Item | Detalhe |
|------|---------|
| Container | `edgeai-kafka` |
| Porta | 9092 |
| Tópico | `sensor-readings` (1 partição, 1 réplica) |
| Modo | KRaft — sem Zookeeper |

**Fluxo:**
1. `MqttSubscriber` deserializa o payload MQTT e publica no tópico `sensor-readings`
2. `SensorConsumer` consome o tópico, chama `DeviceService.findOrCreate()` e `SensorService.saveSensorPayload()`

### Frontend — `frontend/`

| Item | Detalhe |
|------|---------|
| Framework | Next.js 15 App Router + React 19 |
| Porta | 3000 (dev) |
| Estilo | Tailwind CSS 3 (tema escuro) |
| Gráficos | Recharts — `SensorChart` com 3 séries (temperatura, vibração, corrente) |
| Auth | Token JWT em `localStorage` + cookie `jwt_token` para middleware SSR |
| Proxy | `/api/*` → `http://localhost:8082/api/*` (next.config.js rewrites) |

**Páginas:**

| Rota | Descrição |
|------|-----------|
| `/login` | Login com email e senha |
| `/dashboard` | Cards de dispositivos com status e última leitura |
| `/dashboard/readings` | Gráfico de linha com 3 séries (última hora, polling 10s) |
| `/dashboard/anomalies` | Tabela de anomalias com badge vermelho/amarelo por score |

**Componentes principais:**
- `SensorChart` — Recharts `LineChart` agrupando leituras por `HH:mm:ss`; cap de 50 pontos
- `AnomalyTable` — tabela com badge de score: vermelho ≥ 80%, amarelo abaixo
- `usePolling` — hook de polling com `setInterval` e `useRef` para callback estável
- `apiClient` — fetch wrapper com Bearer token; redireciona para `/login` em 401/403

### Redis

| Item | Detalhe |
|------|---------|
| Container | `edgeai-redis` |
| Porta | 6379 |
| Uso atual | Reservado — não utilizado na versão de entrega |

---

## Como Rodar Localmente

### Pré-requisitos

- Docker Desktop (rodando)
- Java 21 (JDK Adoptium)
- Node.js 20+
- Python 3.10+ com `paho-mqtt` e `psycopg2-binary`

### 1. Subir a infraestrutura

```powershell
docker compose up -d
docker compose ps   # todos devem estar healthy
```

### 2. Backend

```powershell
cd backend
./gradlew bootRun
# Disponível em http://localhost:8082
```

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
# Disponível em http://localhost:3000
```

### 4. Simulador ESP32 (tempo real)

```powershell
cd firmware/simulator
python esp32_sensor_simulator.py --anomaly-chance 0.3 --interval 5
```

### 5. Seed histórico (opcional — popula 2 dias de dados)

```powershell
cd firmware/simulator
python seed_historical.py
```

---

## Portas em Uso

| Serviço | Porta | Observação |
|---------|-------|------------|
| Next.js | 3000 | Frontend dev |
| Spring Boot | 8082 | API REST + JWT |
| PostgreSQL (Docker) | 5433 | Remapeado (5432 = PG17 nativo) |
| EMQX MQTT | 1883 | Broker de mensagens |
| EMQX Dashboard | 18083 | Admin do broker |
| Kafka | 9092 | Mensageria |
| Redis | 6379 | Cache (reservado) |

---

## Modelo de Machine Learning — `firmware/models/`

Pipeline de treinamento em Python (`train_model.py`) que:
1. Gera dados sintéticos de sensores industriais
2. Treina um classificador (scikit-learn)
3. Exporta para TFLite
4. Gera o header C `model_data.h` para embarcado no ESP32

O modelo embarcado classifica cada leitura como `normal` ou `anomaly` e calcula um `anomaly_score` (0.0–1.0).

---

## Repositório

Branch principal de desenvolvimento: `feature/esp32-edge-network-sim-bootstrap`

```
edge-ai-industrial/
├── backend/          Spring Boot (Gradle)
├── firmware/         C++ PlatformIO + simulador Python + modelos ML
├── frontend/         Next.js 15
├── database/         Migrations SQL
├── docs/             Plano de implementação, spec, relatório
└── docker-compose.yml
```
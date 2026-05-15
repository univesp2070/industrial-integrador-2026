# Edge AI Industrial — Solo Build Design Spec

**Data:** 2026-05-03  
**Autor:** Kaique Augusto  
**Prazo:** 2026-06-30  
**Contexto:** Projeto originalmente planejado para 5 pessoas. Será executado solo em 58 dias.

---

## 1. Objetivo

Construir e documentar um sistema de monitoramento industrial inteligente com inferência de anomalias em edge (ESP32 + TensorFlow Lite), ingestão de dados via MQTT/Kafka, persistência em PostgreSQL/TimescaleDB, API REST com autenticação JWT, e dashboard Next.js com gráficos de série temporal. O produto final é um **relatório técnico + slides** para apresentação UNIVESP PI-5.

---

## 2. Escopo

### Incluído
- Fluxo ponta-a-ponta: ESP32 (via simulador Python) → EMQX → Spring Boot → Kafka → PostgreSQL → Next.js
- Inferência de anomalia no ESP32 com TFLite (firmware já completo)
- Dashboard com 3 telas: visão geral de dispositivos, gráfico de série temporal, tabela de anomalias
- Autenticação JWT Bearer no backend (usuário fixo em config)
- Kafka como broker de mensagens entre ingestão MQTT e persistência
- Toda infraestrutura rodando local via Docker Compose

### Excluído (corte deliberado)
- Sistema de alertas (email/push notification)
- Suporte a STM32 (apenas ESP32 / simulador Python)
- OAuth2 / cadastro de usuários
- WebSocket / dados em tempo real via push (polling a cada 10s)
- Deploy em servidor remoto

---

## 3. Arquitetura

### Fluxo final (Fase 2+)
```
[Simulador Python / ESP32 físico]
        ↓ MQTT publish (tópico: sensor/data)
[EMQX Broker :1883]
        ↓ MQTT subscribe
[Spring Boot: MqttSubscriber]
        ↓ produce
[Kafka: tópico sensor-readings]
        ↓ consume
[Spring Boot: SensorConsumer → SensorService]
        ↓
[PostgreSQL + TimescaleDB :5432]
        ↓ Spring Data JDBC
[REST API :8080]
        ↓ fetch (polling 10s)
[Next.js Dashboard :3000]
```

### Fluxo Walking Skeleton (Fase 1 — sem Kafka)
```
[Simulador Python]
        ↓ MQTT
[EMQX]
        ↓ MQTT subscribe
[Spring Boot: MqttSubscriber → SensorService direto]
        ↓
[PostgreSQL]
        ↓ REST API
[Next.js]
```
Kafka é inserido na Fase 2 substituindo a chamada direta ao `SensorService`, sem alterar nenhuma outra camada.

### Infraestrutura Docker Compose (existente)
- EMQX :1883 / :18083
- PostgreSQL + TimescaleDB :5432
- Kafka + Zookeeper :9092
- Redis :6379

---

## 4. Backend (Spring Boot 3.3)

### Estrutura de pacotes
```
com.edgeai.industrial/
├── config/       # SecurityConfig, KafkaConfig, MqttConfig
├── domain/       # SensorReading, Device (entidades mapeando schema existente)
├── repository/   # Spring Data JDBC repositories
├── service/      # SensorService, DeviceService
├── controller/   # SensorController, DeviceController, AuthController
├── mqtt/         # MqttSubscriber
├── kafka/        # SensorProducer, SensorConsumer
└── security/     # JwtFilter, JwtService, UserDetailsService
```

### Endpoints REST
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/auth/login` | Retorna JWT (credenciais em application.yml) |
| GET | `/api/devices` | Lista todos os dispositivos |
| GET | `/api/sensors/readings` | Leituras com filtro `?deviceId=&from=&to=` |
| GET | `/api/sensors/latest` | Última leitura por dispositivo |
| GET | `/api/sensors/anomalies` | Leituras com `anomaly_detected = true` |

Todos os endpoints (exceto `/api/auth/login`) exigem `Authorization: Bearer <token>`.

### Segurança
- JWT HS256, validade 24h, segredo em variável de ambiente
- Usuário único fixo em `application.yml` (sem banco de usuários)
- Spring Security com `JwtFilter` antes de `UsernamePasswordAuthenticationFilter`

### Kafka
- Tópico: `sensor-readings` (1 partição, replicação 1 — local only)
- `MqttSubscriber` → `SensorProducer.send(SensorReadingDto)`
- `SensorConsumer` → `SensorService.save(SensorReadingDto)`
- Serialização: JSON via `JsonSerializer` / `JsonDeserializer`

### Banco de Dados
- Schema existente — Spring Boot **não gera** schema (Spring Data JDBC não tem DDL automático; sem `spring.sql.init.mode` ou Flyway configurado, o schema existente é preservado)
- Spring Data JDBC mapeando tabelas existentes: `sensor_readings`, `devices`

---

## 5. Frontend (Next.js 15 + React 19)

### Estrutura de páginas (App Router)
```
app/
├── (auth)/login/          # Formulário de login → armazena JWT no localStorage
├── dashboard/
│   ├── page.tsx           # Cards de status dos dispositivos (online/offline + última leitura)
│   ├── readings/page.tsx  # Gráfico de linha (Recharts) — temperatura, vibração, corrente
│   └── anomalies/page.tsx # Tabela paginada de anomalias detectadas pelo ESP32
└── layout.tsx             # Sidebar + proteção de rota (redirect para /login se sem JWT)
```

### Componentes
- `DeviceCard` — status + última leitura de cada dispositivo
- `SensorChart` — gráfico de linha com Recharts, 3 séries, filtro de período
- `AnomalyTable` — tabela com paginação, colunas: timestamp, device, tipo, score
- `ApiClient` — wrapper de `fetch` que injeta `Authorization: Bearer` automaticamente

### Dados
- Polling via `useEffect` + `setInterval` a cada 10 segundos
- Estado gerenciado com `useState` simples (sem Redux/Zustand)
- Tipos TypeScript para `SensorReading`, `Device`, `AnomalyRecord`

### Visual
- Tailwind CSS (já configurado)
- Design funcional e legível — prioridade em clareza para screenshots do relatório

---

## 6. Cronograma de 8 Semanas

| Fase | Período | Entregas |
|------|---------|----------|
| **1 — Walking Skeleton** | 04–17 mai | Simulador → MQTT → Backend (sem Kafka) → PostgreSQL → 1 gráfico no Next.js |
| **2 — Kafka** | 18–31 mai | Kafka integrado ao fluxo, consumer/producer funcionando, logs evidenciáveis |
| **3 — JWT + Frontend completo** | 01–14 jun | Login/auth, dashboard com 3 telas, tabela de anomalias, endpoints protegidos |
| **4 — Buffer + Relatório** | 15–30 jun | Ajustes, screenshots, vídeo de evidência, escrita do relatório técnico |

---

## 7. Evidências para o Relatório

| Evidência | Como capturar |
|-----------|---------------|
| Infraestrutura rodando | Screenshot do `docker compose ps` com todos os serviços `healthy` |
| Fluxo de dados ponta-a-ponta | Vídeo: simulador enviando → dashboard atualizando |
| Kafka funcionando | Screenshot dos logs do consumer recebendo mensagens |
| Inferência de anomalia | Screenshot da tabela de anomalias com scores do ESP32 |
| Autenticação JWT | Screenshot do header `Authorization: Bearer` numa requisição (DevTools) |

---

## 8. Testes

- **Backend:** Spring Boot Test + banco H2 para testes de integração dos endpoints REST críticos (`/readings`, `/anomalies`, `/auth/login`)
- **Frontend:** Testes manuais documentados no relatório
- **Fluxo end-to-end:** Simulador Python como fixture de teste de integração

---

## 9. O que já está pronto (não precisa construir)

- Firmware ESP32 completo (WiFi, MQTT, TFLite, arquitetura modular)
- Pipeline ML (dataset sintético, modelo 73 parâmetros, export TFLite/C header)
- Docker Compose com todos os serviços
- Schema PostgreSQL/TimescaleDB (8 tabelas)
- Contrato MQTT v1 congelado (JSON schema de `sensor/data` e `device/status`)
- Simulador Python do ESP32

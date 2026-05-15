# Backend API - Cloud Layer (Spring Boot)

Módulo responsável pela API REST do sistema. Recebe dados dos dispositivos via MQTT Broker, aplica regras de negócio e persiste no banco de dados.

## Responsabilidades

- Receber e validar dados dos sensores
- Aplicar regras de negócio adicionais
- Persistência no PostgreSQL/TimescaleDB
- Autenticação e autorização (JWT, OAuth2, RBAC)
- Expor APIs REST para o Frontend
- Integração com Apache Kafka para eventos assíncronos

## Tecnologias

- Java 21
- Spring Boot 3.x
- Spring Security
- Spring Data JPA
- Spring WebSocket
- Gradle
- PostgreSQL + TimescaleDB
- Apache Kafka Client

## Estrutura

```
backend/
├── src/
│   ├── main/
│   │   ├── java/com/edgeai/industrial/
│   │   │   ├── BackendApplication.java
│   │   │   ├── config/           # Security, CORS, Kafka, WebSocket
│   │   │   ├── controller/       # REST Controllers
│   │   │   ├── service/          # Business logic
│   │   │   ├── repository/       # Data access
│   │   │   ├── model/            # Entities / DTOs
│   │   │   ├── mqtt/             # MQTT message handlers
│   │   │   ├── kafka/            # Kafka producers/consumers
│   │   │   └── security/         # Auth filters, JWT utils
│   │   └── resources/
│   │       ├── application.yml
│   │       └── application-dev.yml
│   └── test/
│       └── java/com/edgeai/industrial/
├── build.gradle
└── settings.gradle
```

## Executar

```bash
./gradlew bootRun

# Testes
./gradlew test
```

# Database - PostgreSQL + TimescaleDB

Módulo com migrations e seeds do banco de dados.

## Responsabilidades

- Armazenamento de dados temporais (TimescaleDB)
- Histórico de eventos dos sensores
- Dados de usuários e configurações
- Dados de dispositivos registrados

## Tecnologias

- PostgreSQL 16
- TimescaleDB (extensão para time-series)

## Migrations

As migrations seguem o padrão de versionamento sequencial:

```
V001__create_devices_table.sql
V002__create_sensor_data_table.sql
V003__create_users_table.sql
V004__create_alerts_table.sql
```

## Executar migrations

```bash
# Via Flyway (integrado ao Spring Boot)
# As migrations são aplicadas automaticamente ao iniciar o backend
```

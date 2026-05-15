# Sistema Embarcado Inteligente - Edge AI Industrial

> Arquitetura de System Design Completa para monitoramento industrial inteligente com Edge AI, IoT e Cloud.

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)

## 📋 Visão Geral

Sistema completo de monitoramento industrial que integra sensores de prateleira com inteligência artificial na borda (Edge AI), comunicação IoT segura e uma plataforma cloud para visualização em tempo real e alertas.

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
│   EDGE LAYER    │    │   NETWORK    │    │      CLOUD LAYER        │    │   DATABASE   │    │  WEB LAYER   │    │     ALERTS       │
│                 │    │              │    │                         │    │              │    │              │    │                  │
│ [1] Sensores    │I2C │ IoT Comm     │MQTT│ [4] MQTT Broker (EMQX)  │    │ [7] PostgreSQL│REST│ [8] Frontend │Push│ [9] Alertas      │
│ [2] ESP32/STM32 │───▸│ Layer        │───▸│ [5] Backend API (Spring)│───▸│   TimescaleDB │───▸│   Next.js    │───▸│   Web Push       │
│ [3] Motor IA    │    │ MQTT + TLS   │    │ [6] Kafka Streaming     │    │              │    │   TypeScript │    │   Email          │
└─────────────────┘    └──────────────┘    └─────────────────────────┘    └──────────────┘    └──────────────┘    └──────────────────┘
```

## 📦 Módulos do Sistema

| # | Módulo | Tecnologia | Descrição |
|---|--------|------------|-----------|
| 1 | Sensores de Prateleira | I2C / SPI / GPIO | Leitura digital/analógica, coleta em tempo real |
| 2 | Microcontrolador | ESP32/STM32 + C/C++ | Firmware com TensorFlow Lite Micro, inferência local |
| 3 | Motor de Inferência | TFLite Micro | Classificação, detecção de anomalias, geração de eventos |
| 4 | MQTT Broker | EMQX | Gerenciamento de tópicos, escalável horizontalmente |
| 5 | Backend API | Java + Spring Boot | Spring Security, validação, regras de negócio, persistência |
| 6 | Event Streaming | Apache Kafka | Processamento assíncrono de eventos |
| 7 | Banco de Dados | PostgreSQL + TimescaleDB | Dados temporais, histórico de eventos |
| 8 | Frontend | Next.js + TypeScript | Dashboard tempo real, WebSocket, indicadores visuais |
| 9 | Sistema de Alertas | Web Push / Email | Notificações em tempo real, integração externa |

## 🔒 Segurança

- TLS end-to-end
- JWT + OAuth2
- RBAC (Role-Based Access Control)
- Certificados por dispositivo

## 📈 Escalabilidade

- Kubernetes
- Backend stateless
- Cluster MQTT
- Cache Redis
- OTA update para dispositivos

## 📁 Estrutura do Repositório

```
edge-ai-industrial/
├── firmware/                    # Edge Layer - ESP32/STM32
│   ├── src/                     # Código-fonte do firmware
│   ├── lib/                     # Bibliotecas customizadas
│   ├── models/                  # Modelos TFLite
│   ├── test/                    # Testes unitários
│   └── platformio.ini           # Configuração PlatformIO
├── backend/                     # Cloud Layer - Spring Boot API
│   ├── src/main/java/           # Código-fonte Java
│   ├── src/main/resources/      # Configurações
│   └── build.gradle             # Build Gradle
├── frontend/                    # Web Layer - Next.js
│   ├── src/                     # Código-fonte React/Next.js
│   ├── public/                  # Assets estáticos
│   └── package.json             # Dependências Node.js
├── streaming/                   # Event Streaming - Kafka
│   └── config/                  # Configurações Kafka
├── broker/                      # MQTT Broker - EMQX
│   └── config/                  # Configurações EMQX
├── database/                    # Database - PostgreSQL + TimescaleDB
│   ├── migrations/              # Migrations SQL
│   └── seeds/                   # Dados iniciais
├── alerts/                      # Sistema de Alertas
│   └── src/                     # Serviço de notificações
├── infra/                       # Infraestrutura
│   ├── docker/                  # Dockerfiles
│   ├── k8s/                     # Manifests Kubernetes
│   └── terraform/               # IaC com Terraform
├── docs/                        # Documentação
│   ├── architecture/            # Diagramas de arquitetura
│   ├── api/                     # Documentação de APIs
│   └── guides/                  # Guias de desenvolvimento
├── .github/                     # GitHub configs
│   ├── workflows/               # CI/CD pipelines
│   ├── ISSUE_TEMPLATE/          # Templates de issues
│   └── PULL_REQUEST_TEMPLATE.md # Template de PR
├── docker-compose.yml           # Orquestração local
└── Makefile                     # Comandos úteis
```

## 🔀 Git Flow

Este projeto utiliza **Git Flow** para gerenciamento de branches:

| Branch | Propósito |
|--------|-----------|
| `main` | Código em produção, sempre estável |
| `develop` | Branch de integração, próxima release |
| `feature/*` | Novas funcionalidades |
| `release/*` | Preparação de release |
| `hotfix/*` | Correções urgentes em produção |
| `bugfix/*` | Correções de bugs em develop |

### Convenção de Branches

```
feature/firmware-sensor-integration
feature/backend-auth-module
feature/frontend-dashboard
feature/kafka-event-processing
bugfix/mqtt-connection-timeout
hotfix/security-patch-tls
release/v1.0.0
```

### Convenção de Commits

```
feat: adiciona leitura de sensores I2C
fix: corrige timeout na conexão MQTT
docs: atualiza documentação da API
refactor: reestrutura módulo de inferência
test: adiciona testes para o motor de IA
ci: configura pipeline de deploy
chore: atualiza dependências
```

## 🚀 Quick Start

```bash
# Clone o repositório
git clone https://github.com/Zezoca29/edge-ai-industrial.git
cd edge-ai-industrial

# Suba a infraestrutura local
docker-compose up -d

# Firmware (requer PlatformIO)
cd firmware && pio run

# Backend
cd backend && ./gradlew bootRun

# Frontend
cd frontend && npm install && npm run dev
```

## 👥 Equipe

Para contribuir, siga o fluxo:

1. Crie uma branch a partir de `develop`: `git checkout -b feature/sua-feature develop`
2. Faça seus commits seguindo a convenção
3. Abra um Pull Request para `develop`
4. Aguarde code review de pelo menos 1 membro
5. Após aprovação, faça merge

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

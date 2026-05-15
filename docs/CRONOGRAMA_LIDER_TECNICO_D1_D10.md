# Cronograma de Execução (D1 a D10) — Líder Técnico

Data de referência: 2026-04-02
Responsável: Líder Técnico (Firmware + Integração)
Base: `docs/PLANO_DE_ACAO.md`, `docs/EDGE_NETWORK_ESP32_ACTION_PLAN.md`, `docs/api/BACKEND_EDGE_INGESTION_REQUIREMENTS.md`

## Objetivo dos 10 dias

Entregar o fluxo validado:
`Simulador/ESP32 -> MQTT (EMQX) -> Backend -> Banco (devices/sensor_data/alerts)`
com contrato estável, critérios de aceite fechados e time sincronizado.

## Cadência diária do líder (fixa)

1. Daily de 15 min: bloqueios, prioridade do dia, dono por tarefa crítica.
2. Check técnico de 20 min: contrato MQTT + status de integração.
3. Checkpoint fim do dia (10 min): o que foi entregue, risco aberto, plano D+1.

## D1 — Kickoff técnico + congelar contrato v1

Objetivo: alinhar todo o time no contrato e no fluxo de integração.

Tarefas do líder:
1. Congelar tópicos MQTT e payload v1 (`sensor/data/{device_id}`, `device/status/{device_id}`).
2. Publicar decisão de formato de units e timezone (UTC ISO-8601).
3. Apresentar critérios de aceite da Fase 1 para todos os devs.
4. Abrir quadro de tarefas por dono (Backend1, Backend2, Front1, Front2, Líder).

Entregável do dia:
1. Contrato v1 aprovado pelo time.
2. Board com tarefas priorizadas e dependências explícitas.

Gate de saída D1:
1. Ninguém inicia implementação sem o contrato v1 assinado pelo time.

## D2 — Simulação Edge sem hardware

Objetivo: provar envio de dados sem ESP32 físico.

Tarefas do líder:
1. Rodar simulador em `--dry-run` e depois apontando para EMQX local.
2. Demonstrar mensagens em tópicos corretos no broker.
3. Definir frequência padrão de publicação e parâmetros de teste.
4. Registrar caso de teste base para repetição diária.

Entregável do dia:
1. Simulador publicando dados válidos no EMQX.
2. Roteiro de teste local documentado.

Gate de saída D2:
1. Fluxo `simulador -> broker` reproduzível por qualquer dev do time.

## D3 — Base de firmware modular

Objetivo: preparar código do firmware para evolução real.

Tarefas do líder:
1. Estruturar módulos `config`, `communication`, `sensors`, `inference` (interfaces/stubs).
2. Ajustar `main.cpp` para fluxo real de setup/loop com chamadas modulares.
3. Definir macro de modo simulação vs modo hardware real.
4. Fechar checklist de build local do firmware (mesmo sem sensor físico).

Entregável do dia:
1. Arquitetura de firmware modular inicial pronta para crescer.

Gate de saída D3:
1. Build compila e loop lógico está padronizado.

## D4 — Integração com Backend (ingestão MQTT)

Objetivo: iniciar validação ponta-a-ponta com backend.

Tarefas do líder:
1. Alinhar com Backend2 assinatura dos tópicos MQTT.
2. Validar campos obrigatórios de parsing com Backend1.
3. Executar teste conjunto de ingestão com payload real do simulador.
4. Registrar divergências de contrato e corrigir no mesmo dia.

Entregável do dia:
1. Backend consumindo mensagens sem erro estrutural de payload.

Gate de saída D4:
1. Mensagens de `sensor/data/+` e `device/status/+` aceitas pelo backend.

## D5 — Persistência no banco + revisão de mapeamento

Objetivo: garantir dados chegando no schema atual.

Tarefas do líder:
1. Validar atualização em `devices` (`status`, `last_seen_at`, `firmware_version`).
2. Validar inserção em `sensor_data` (1 linha por métrica).
3. Revisar com backend uso de `metadata` JSONB para contexto completo.
4. Confirmar consultas SQL de validação operacional.

Entregável do dia:
1. Primeira carga de dados persistida em banco a partir do simulador.

Gate de saída D5:
1. `SELECT` de validação retorna dados consistentes para pelo menos 1 dispositivo.

## D6 — Regra de alerta (anomaly_score)

Objetivo: fechar ciclo com geração de alertas.

Tarefas do líder:
1. Definir threshold inicial com backend (ex.: `0.8`).
2. Ajustar simulador para produzir eventos anômalos de forma controlada.
3. Testar criação de `alerts` com severidade e mensagem padronizada.
4. Definir regra simples de deduplicação para evitar spam.

Entregável do dia:
1. Alertas automáticos gerados por evento anômalo.

Gate de saída D6:
1. Pelo menos 1 alerta criado e auditável por payload de origem.

## D7 — Resiliência de rede

Objetivo: validar comportamento em falha e reconexão.

Tarefas do líder:
1. Testar reinício do broker durante publicação.
2. Testar reconexão e retomada de envio sem travamento.
3. Validar comportamento para payload malformado.
4. Revisar timeout/retry/backoff junto ao backend.

Entregável do dia:
1. Matriz de falhas com comportamento esperado vs observado.

Gate de saída D7:
1. Recuperação após falha de broker comprovada.

## D8 — Validação com frontend (consumo de dados reais)

Objetivo: garantir que dados edge chegam até camada web.

Tarefas do líder:
1. Sincronizar formato de resposta com Front2.
2. Validar `GET /api/devices`, `/api/sensors/latest/{deviceId}`, `/api/alerts`.
3. Garantir que frontend exibe dado real e não mock para 1 fluxo principal.
4. Revisar campos necessários para gráficos e status de device.

Entregável do dia:
1. Frontend consumindo dados reais de pelo menos 1 dispositivo simulado.

Gate de saída D8:
1. Fluxo visível ponta-a-ponta em tela para demo interna.

## D9 — Teste de estabilidade (soak test)

Objetivo: testar estabilidade contínua antes do fechamento.

Tarefas do líder:
1. Executar carga contínua por 1 hora com simulador.
2. Monitorar perda de mensagem, reconexões e latência percebida.
3. Validar crescimento esperado em `sensor_data` e `alerts`.
4. Consolidar bugs finais e definir correções mínimas de release.

Entregável do dia:
1. Relatório curto de estabilidade (1h) com evidências.

Gate de saída D9:
1. Sem falha crítica impeditiva no fluxo principal.

## D10 — Fechamento técnico da sprint

Objetivo: concluir a evolução e preparar próxima etapa (hardware real).

Tarefas do líder:
1. Fechar checklist de aceite das Fases 1 e 2 do plano geral.
2. Consolidar handoff técnico para backend/frontend com pontos pendentes.
3. Definir backlog da próxima sprint (OTA, TFLite real, sensor físico).
4. Fazer demo de fluxo completo para o time.

Entregável do dia:
1. Sprint encerrada com evidência de fluxo ponta-a-ponta funcional.
2. Próxima sprint planejada com prioridades e riscos.

Gate de saída D10:
1. Decisão formal: pronto para iniciar integração com hardware real.

## Quadro de dependências críticas

1. Se backend ingest não estiver pronto até D4, manter trilha de simulação + validação no broker e antecipar resiliência (D7).
2. Se endpoints REST atrasarem, validar por SQL e manter frontend em modo híbrido temporário.
3. Se regra de alerta oscilar, congelar threshold em configuração externa e seguir com valor conservador.

## Riscos e mitigação (foco do líder)

1. Risco: time começar com payload diferente.
Mitigação: contrato v1 único e revisão diária.

2. Risco: backend persistir errado o `sensor_data`.
Mitigação: teste com payload conhecido + query de verificação por métrica.

3. Risco: atraso por falta de hardware.
Mitigação: simulador como caminho oficial de desenvolvimento até chegada do sensor.

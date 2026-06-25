# Arquitetura do Repositório Template — SDLC Autônomo

Artefato 3. Repo template (Claude Code plugin + serviço) que projetos clonam e especializam.
Requisitos: rodar com **sandbox**, ser **deployável na cloud conteinerizado**, e ser
**trigável por (a) devs manualmente OU (b) webhooks de Jira/ADO/similar**. Deriva do flow +
checklist de enforcement já aprovados (workinprogress/autonomous-sdlc-template/).

## Princípio: dois modos, um core
O MESMO pipeline (DoR → ... → PR) roda em dois modos de invocação, sem duplicar lógica:
- **Modo dev (local/interativo):** o dev roda um comando (CLI/slash do plugin Claude Code).
- **Modo serviço (autônomo/headless):** um webhook do board dispara o pipeline sem humano
  presente (ex.: card → "Ready" → flow inicia).
O core do orquestrador é o mesmo; muda só o ENTRYPOINT e o nível de interação.

## Componentes

### 1. Core do orquestrador (a lógica do flow)
Implementa o pipeline aprovado. Agnóstico de invocação. Claude = orquestrador; subagentes
isolados executam. Lê config do projeto (board, stacks, matriz de risco, DoR/DoD, thresholds).
Empacotado como **Claude Code plugin** (skills/commands) + uma camada de serviço headless
(Claude Agent SDK self-hosted, subprocess model) p/ o modo autônomo. **O core/worker roda com a
identidade do AGENTE (permissão mínima) e NÃO tem poderes de admin** — ver Componente 7.

### 2. Entrypoint A — CLI/plugin (modo dev)
Comando do plugin (ex.: `/work <id>`) que o dev roda na sua máquina/sandbox. Interativo:
respeita os checkpoints humanos (✋) síncronos. É o modo de menor blast-radius (humano no loop).
Entrypoint FINO: toda diferença de modo vem de um **adapter de interação/aprovação** injetado
(síncrono no dev, durável no serviço) — sem atalhos de dev-mode que divirjam do serviço.

### 3. Entrypoint B — Webhook ingester (modo serviço)
Serviço HTTP que recebe webhooks de Jira/ADO (via **adapter de board**). Responsabilidades:
- **Verificar assinatura** do webhook (HMAC/secret) + **janela de replay** (rejeita evento velho).
- **Idempotência DURÁVEL** (store de event-id; dedup mesmo após restart) + **lock por ticket/job**
  (não processar o mesmo card 2x em paralelo).
- **Canonicalização por provider** (Jira/ADO mandam shapes diferentes → evento normalizado).
- **Filtrar** o evento (só dispara em transições configuradas, ex.: → Ready).
- **Enfileirar** um job (responde 200 rápido, processa async). **Dead-letter** p/ evento que falha.
Nunca executa o agente no processo do ingester (separação: ingestão ≠ execução).

### 4. Fila + Worker efêmero (execução isolada)
- **Queue** (durável, autenticada) desacopla ingestão de execução; retry, backpressure, DLQ.
- **Worker** puxa o job e roda o core num **sandbox EFÊMERO por job** (k8s Agent Sandbox /
  ephemeral pod). Blast-radius contido: 1 job = 1 sandbox, destruído no fim (**cleanup garantido**,
  mesmo em falha). **Egress de rede restrito** (allowlist), **secrets escopados por job**
  (injetados no job, não na imagem), **política de retenção** de artefatos definida.
- Worker roda com identidade do AGENTE (sem admin no VCS).
- Estado do job é **retomável** (checkpoint & resume) — se o worker morre, outro retoma.
  **Job ID canônico** (derivado do event-id do board) liga webhook→job→PR; **resume é idempotente**
  através de retry/DLQ (retomar um job não duplica trabalho nem PR já criado).

### 4b. Componente de APROVAÇÃO durável (checkpoints ✋ no headless) — first-class
No modo serviço não há humano síncrono. Os ✋ obrigatórios viram um **serviço de aprovação durável**:
o job PAUSA num checkpoint persistido, registra **identidade do aprovador** + valida **política de
autorização** (QUEM pode aprovar O QUÊ — ex.: só owner da capacidade hard-sensitive aprova gate
hard-sensitive; aprovador ≠ quem disparou), espera decisão (approve/reject) com **timeout →
escalation**, e só então RETOMA. Auditável (quem/quando/o quê).
Notificação (Teams/Slack) só avisa; a trava é o checkpoint durável, não a notificação.

### 5. Adapters (tiers de capability — core vs opcional)
Contratos NORMALIZADOS (capability genérica + fallback por provider), projeto pluga o seu:
- **Board adapter** (Jira / ADO): `on_webhook(event)`, `transition(ticket,state)`,
  `create_ticket(...)`, `comment(...)`. CORE.
- **VCS adapter** (GitHub/ADO Repos): operações de RUNTIME do agente apenas — abrir PR, ler
  status de checks, push em branch de feature. branch protection/required checks/CODEOWNERS são
  LIDOS, não administrados pelo agente (ver Componente 7). CORE.
- **CI/CD adapter**: dispara/lê status dos required checks. CORE.
- **Notification adapter** (Teams/Slack): escalations, ✋. OPCIONAL.

### 6. Config do projeto (setup)
`config.{yaml,json}` versionado: board, repos, stacks, matriz de risco + limiar, DoR/DoD
(referência aos artefatos em wiki/git), gates ativos, deploy on/off.

### 7. Plano de ADMIN/BOOTSTRAP — SEPARADO do agente (controlado por humano)
Materializar enforcement (pre-commit, PR template, CODEOWNERS, workflows, branch protection,
rulesets) e **criar a identidade escopada do agente** são operações de ADMIN. Rodam num caminho
**separado, com credencial de admin humano**, INDISPONÍVEL ao orquestrador/worker. O agente NUNCA
provisiona a própria identidade nem altera o próprio enforcement (Princípio nº0/nº1 do checklist).
O setup é executado por um humano/admin (ou pipeline de admin com aprovação), não pelo flow.
**Boundaries de rede/IAM:** o worker roda numa rede/role que NÃO alcança os scripts de admin nem
consegue assumir a role de admin (sem path de privilege-escalation do runtime pro bootstrap).

## Deploy (conteinerizado, cloud)
- **Imagem base** do worker: runtime + Claude Agent SDK + ferramentas de gate (scanners, test
  runners) — ou o worker provisiona toolchain por stack.
- **Ingester**: serviço HTTP stateless (escala horizontal; ex.: Cloud Run / container service).
- **Worker**: jobs efêmeros (k8s Jobs / Cloud Run Jobs / ephemeral pods) — 1 por tarefa.
- **Queue**: serviço gerenciado (SQS/PubSub/Redis Stream) — adapter.
- **Secrets**: vault/secret manager; NUNCA no repo. Identidade do agente ≠ identidade humana.
- **Observabilidade:** audit trail (decisões/delegações), logs estruturados, **trace correlation
  webhook→job→PR** (um id que liga o evento ao job ao PR), **cost ceiling/token budget por job**
  (aborta/escala ao estourar), **detecção de stuck-job**, e **runbooks de operador**.
Tudo parametrizável: um projeto pode rodar só o modo dev (sem ingester/queue) ou o stack completo.

## Estrutura do repo (esqueleto)
```
/                      README, LICENSE, CONTRIBUTING
.claude-plugin/        plugin.json, marketplace.json   (modo dev)
skills/                pipeline skills (DoR, spec, plan, dev-loop, review, PR...)
core/                  orquestrador agnóstico de invocação
service/
  ingester/            webhook HTTP (assinatura, replay, idempotência durável, lock, enqueue)
  worker/              consome fila, roda core em sandbox efêmero (cleanup garantido)
  approval/            serviço de aprovação durável (✋ no headless: pause/resume, timeout)
adapters/
  board/{jira,ado}/    board adapter (capability normalizada + fallback)
  vcs/{github,ado}/    vcs adapter (RUNTIME do agente: PR, status; NÃO admin)
  ci/  notify/
admin/                 BOOTSTRAP separado (credencial humana): materializa enforcement +
                       cria identidade escopada do agente — INDISPONÍVEL ao agente/worker
enforcement/           pre-commit, PR template, CODEOWNERS, workflows, rulesets (templates)
deploy/                Dockerfile(s), compose (local sandbox), k8s/cloud manifests
config/                config.example.yaml + schema + risk-matrix.example
docs/                  modelo, processo, runbook (artefato 2 mora aqui)
tests/                 lint, evals das skills, testes dos adapters
```

## O que NÃO é
Não acopla a um board/VCS específico (tudo via adapter). Ingester NÃO executa o agente
(separação ingestão/execução). Worker é efêmero (não um daemon long-lived que acumula estado).
Sodexo é um CONSUMIDOR do template (implementa adapters ADO), não o template em si.

## Ordem de construção (incremental)
1º core + modo dev (plugin/CLI) — entrega valor sem infra. 2º enforcement materializado pelo
**admin path** (separado, no setup). 3º adapters board/vcs. 4º **serviço de aprovação durável**
(pré-requisito do headless). 5º ingester + queue + worker efêmero (modo serviço, depende do 4º).
6º deploy cloud (container/manifests). 7º observabilidade/audit/token-budget. 8º field test Sodexo
(adapters ADO).

# Autonomous SDLC

Estrutura agêntica autônoma de desenvolvimento de software — cobre **todas as etapas do SDLC**,
operável como **full-agentes** ou **agentes + humanos** conforme o risco/complexidade da tarefa.
Entregue como um **plugin/template do Claude Code** que projetos adotam e especializam.

**Princípio central:** um agente nunca é o oráculo da própria prova. "Done" é uma pilha de sinais
ortogonais; o juiz de IA é a camada *advisory* final, nunca a única. Claude orquestra, agentes
isolados executam, e a infraestrutura — não a boa vontade do agente — garante o enforcement.

## Navegação

| Onde | O quê |
|---|---|
| [`docs/README.md`](docs/README.md) | **Documentação** — funcionamento do modelo e do processo, etapa por etapa. |
| [`deck/deck-script.md`](deck/deck-script.md) | **Deck** — script de apresentação slide a slide. |
| [`docs/model/autonomous-workflow-model.md`](docs/model/autonomous-workflow-model.md) | O flow do SDLC (normativo). |
| [`docs/model/enforcement-controls-checklist.md`](docs/model/enforcement-controls-checklist.md) | Controles de enforcement configurados no setup. |
| [`docs/model/repo-architecture.md`](docs/model/repo-architecture.md) | Arquitetura do repositório template (sandbox, cloud, webhook). |

## O flow, em uma linha

DoR (bloqueio) → risco → grounding → requisitos → spec + AC testável (QA shift-left) [✋] → escopo
→ plano + juiz de modelo diferente [✋] → decomposição → dev loop (implementer → reviews) → gate
DoD ortogonal → review holístico → PR [✋ merge] → DEV-DONE → [opt-in: deploy → health → rollback].

## Status

Modelo, controles de enforcement e arquitetura **validados** por revisão adversarial independente
(GO). Próximos passos: materializar o repositório template (core + modo dev primeiro) e field test
no projeto de referência.

## Requisitos do repositório template (alvo)

- Rodar com **sandbox** (isolamento de execução).
- **Deployável na cloud, conteinerizado.**
- Trigável por **devs (CLI/plugin)** ou por **webhooks de Jira/ADO**.

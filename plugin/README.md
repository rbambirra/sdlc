# SDLC Autônomo — Plugin (MVP)

Implementação do template SDLC autônomo, **portável entre harnesses** (Claude, Codex, Hermes).
Ver o plano e o modelo em `../docs/`. Status: MVP em construção (modo dev primeiro).

## Portabilidade (3 camadas)
- `skills/` + `AGENTS.md` — comportamento neutro (markdown).
- `core/capabilities.py` — CONTRATO neutro (o seam). O core nunca conhece o harness.
- `adapters/harness/<x>/` — adapter fino por harness; passa a conformance suite p/ ser "suportado".

## Rodar os testes
```
cd plugin && python3 -m pytest -v
```
21 testes (offline, mocks). Adicione `-m integration` para exercitar os CLIs
reais (Claude/Codex) contra o contrato — pula sozinho se o CLI não estiver no PATH.

## Fake scenario — teste end-to-end SEM mock
Prova que o core dirige um harness REAL (Codex/Claude) por TODAS as fases do
pipeline. Harness = real (modelo de verdade); Board/Vcs = fakes in-memory (sem
Jira/ADO/GitHub real). Roles "builder" (implementer) rodam num worktree isolado
e escrevem/rodam código de verdade; roles analíticos retornam artefato como texto.

Lento e consome tokens — rode sob demanda, não no CI:
```
cd plugin && python3 scenarios/fake_scenario.py          # codex + claude
cd plugin && python3 scenarios/fake_scenario.py codex     # só codex
cd plugin && python3 scenarios/fake_scenario.py claude     # só claude
```
PASS = pipeline chega a DEV-DONE com PR aberto (no Vcs fake).


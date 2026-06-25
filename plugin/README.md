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

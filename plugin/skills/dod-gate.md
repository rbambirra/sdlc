# Skill: Gate DoD ortogonal

**Quando:** após o dev loop, antes do review holístico. Decide "done".

## "Done" nunca é um único teste verde
É a **conjunção** de sinais ortogonais (introduzidos incrementalmente):
- [ ] **Held-out tests** — ISOLADOS, fora do alcance do implementer; rodados pela CI. (anti reward-hacking)
- [ ] **Mutation score** ≥ limiar (qualidade da suíte, não só cobertura).
- [ ] **Type-check / lint / compile.**
- [ ] **Contrato / OpenAPI** (drift FE↔BE).
- [ ] **Deps scan** (CVE + anti-slopsquatting).
- [ ] **Secret scanning de código** (bloqueia merge — credencial no git history já é incidente).
- [ ] **SAST** para mudança security-relevant.
- [ ] **E2E real** (auth real, serviços juntos) — DENTRO do gate, não passo separado no fim.

## Regra
Os held-out tests rodam via `run_gate` no core, NUNCA dentro do subagente implementer. Qualquer
gate CORE falho bloqueia. Provisionamento de secrets de INFRA é trilha de deploy (separada).

# Skill: Definition of Ready (DoR)

**Quando:** primeira fase do pipeline, antes de qualquer trabalho. Bloqueio duro de ENTRADA.

## Objetivo
Decidir se o work item está **pronto para ser desenvolvido e testado**. Se reprovar, o item
NÃO entra no flow — volta pro board com o motivo.

## Critérios (o conjunto base; o setup do projeto especializa e versiona em wiki/git)
- [ ] Título e descrição presentes e claros.
- [ ] Critérios de aceite (AC) presentes e não-vazios.
- [ ] Dependências resolvidas ou explicitamente mapeadas (não há bloqueio externo aberto).
- [ ] Escopo cabe numa unidade entregável (não é um épico inteiro).
- [ ] Sem ambiguidade que impeça começar (perguntas em aberto resolvidas).

## Saída
- **PASS** → segue pra classificação de risco.
- **FAIL** → bloqueia, comenta no board o(s) critério(s) não atendido(s), encerra.

## Regra
O critério é definido no setup e documentado em wiki/git. O agente APLICA o critério, não o
inventa. Mudança no critério exige aprovação humana registrada.

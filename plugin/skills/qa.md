# Skill: Agente de QA

**Quando:** três momentos, como papel distinto do implementer e do juiz de código.

## Ownership
QA cuida de **testabilidade e casos de teste**. BA/produto cuida de **intent e escopo**. O
**oráculo isolado** (held-out tests) é responsabilidade do gate (I2), NÃO do QA.

## Momento 1 — BA (shift-left)
Deriva AC testável (Given-When-Then) + matriz de casos (happy + edge) ANTES do código. AC
ambígua/não-testável bloqueia o avanço (humano aprova mudança de escopo).

## Momento 2 — Code review
Verifica **cobertura vs AC**: cada AC tem teste? edge cases? o teste prova a AC ou só passa?
Produz findings de cobertura pra triagem. NÃO é o oráculo held-out (isso é o gate).

## Momento 3 — E2E / validação de fluxo
Mapeia os casos do Momento 1 → cenários. Garante que a validação (browser E2E p/ FE; API
validation p/ BE; ambos p/ FE+BE) cobre a AC e reflete o escopo. Verde = parte do gate de done.

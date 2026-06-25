# Skill: Spec + AC testável (QA shift-left)

**Quando:** após DoR e classificação de risco. Produz a especificação e os critérios de aceite
testáveis ANTES de qualquer código.

## Objetivo
Escrever uma spec que **reconcilia** o intent do work item com as **restrições reais do repo/
runtime** (contratos existentes, migrations, feature flags, auth, constraints operacionais). O
ticket é o intent; o código/runtime é a restrição. "Ticket é a verdade" sozinho gera spec errada.

## Papel do QA (shift-left)
O agente de QA participa AQUI, antes do código:
- Deriva/critica **AC testável** no formato Given-When-Then (ou EARS).
- Propõe a **matriz de casos de teste** (happy + edge).
- Marca AC ambígua/não-testável como **bloqueio** (humano aprova mudança de escopo).
QA cuida de testabilidade; BA/produto cuida de intent e escopo.

## Saída
- Documento de spec + AC testável + matriz de casos de teste.
- Insumo direto pro /test-plan e pra fase de E2E.

## Gate
Spec aprovada antes de qualquer código (hard gate). Checkpoint humano se o risco exigir.

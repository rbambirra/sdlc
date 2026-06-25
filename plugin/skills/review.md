# Skill: Review holístico + triagem

**Quando:** após o gate DoD passar, antes do PR.

## Objetivo
Um **juiz independente** (modelo diferente) revisa o codebase inteiro (não só o diff). Cada
achado entra na **autoridade de triagem**.

## Triagem
- **Severidade:** block / fix-now / defer-com-ticket / wontfix-com-justificativa.
- **Conflito:** gate determinístico vence juiz advisory no status factual; o advisory não derruba
  um gate verde nem aprova um vermelho.
- **Teto de retries** por finding e por tarefa → estourou, escala humano (não re-tenta o mesmo
  subagente sem mudar nada).

## Saída
GO holístico → segue pro PR. Findings block/fix-now → fix loop (com teto) → re-review.

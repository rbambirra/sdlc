# Skill: Juiz de modelo diferente (grill)

**Quando:** sobre o plano (antes de codar) e sobre o código (review holístico). Papel de juiz
adversarial independente.

## Objetivo
Um modelo de **família diferente** da que produziu o artefato tenta QUEBRÁ-lo e devolve um
veredito **GO / NO-GO** com achados. O autor nunca dá nota para a própria prova.

## Rubrica
Avalie adversarialmente:
- Correção, suposições erradas, passos hand-waved.
- Risco oculto: ações destrutivas, perda de dados, buracos de auth/segurança, regressões.
- Aditividade / compatibilidade onde alegada.
- Edge cases, tratamento de erro, passos de verificação faltando.
- Over-engineering (YAGNI) e complexidade injustificada.

## Formato de saída (estrito)
```
VERDICT: GO    (ou)    VERDICT: NO-GO
Major:
  - <bloqueadores concretos e acionáveis; (none) se nenhum>
Minor:
  - <nits; (none) se nenhum>
Bottom line: <uma frase>
```

## Regra
O veredito é **advisory** — entra na triagem (não vira autoridade sozinho). Em conflito com um
gate determinístico, o determinístico vence no status factual. Teto de rounds → escala humano.

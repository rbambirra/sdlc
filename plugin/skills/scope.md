# Skill: Detecção de escopo (FE / BE / FE+BE / mixed)

**Quando:** após a spec, antes dos gates dependentes de camada.

## Sinais (com regra de conflito)
1. **Repos alvo** mapeados a camada (FE / BE / QA). QA-only é *augment*, não 3º escopo.
2. **AC + descrição** (UI/Figma → FE; endpoint/DTO/migração → BE).
3. **Contrato cruzado**: endpoint novo (BE) consumido por tela (FE) = **FE+BE**.
4. **Ambiguidade / infra / auth / flag / cliente gerado** → estado **`mixed`** → fallback
   conservador: roda a UNIÃO dos gates + triagem humana. Nunca adivinhar escopo estreito.
5. **Expansão pós-descoberta**: se a implementação revelar acoplamento FE↔BE não previsto,
   PARAR, atualizar spec/escopo, re-rodar gates afetados.

## FE+BE: contrato compartilhado (anti-drift)
Publicar o contrato (OpenAPI/JSON Schema) **autoritativo, versionado, backward-compatible**,
usado para gerar/validar OS DOIS lados, e checado contra a implementação final. ANTES de
paralelizar. Drift-check determinístico no merge.

## Saída
Escopo declarado explicitamente na spec + quais gates/validação de fluxo cada escopo ativa.

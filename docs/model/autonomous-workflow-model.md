# Estrutura Agêntica Autônoma de Desenvolvimento de Software (SDLC Template)

## Objetivo do produto
Estrutura agêntica autônoma que cobre TODAS as etapas do SDLC, operável como **full-agentes**
ou **agentes+humanos** conforme a complexidade/risco da tarefa. Entregáveis: (1) desenho da
solução, (2) proposta do flow, (3) um **PLUGIN do Claude Code que serve de TEMPLATE** para
projetos adotarem e adicionarem suas especificidades. Field test: Sodexo (sodexo-sdlc).

## Axiomas de arquitetura
- **Claude é o ORQUESTRADOR**: mantém estado, decide, delega, faz triagem. NUNCA implementa
  diretamente. Todo trabalho real (implementar, revisar, QA, julgar) roda em **subagentes de
  contexto isolado** (o orquestrador repassa contexto explícito; subagente não herda histórico).
- "Done" e "Ready" não são hardcoded: são **definidos no SETUP do plugin** e documentados em
  Confluence/wiki/git — acessíveis e atualizáveis. O flow apenas APLICA o critério.
- Verificação é pilha de sinais ortogonais. Juiz LLM é advisory final, nunca a única fonte.
  Linguagem honesta: "mitiga", não "fecha".
- É um TEMPLATE: tudo específico (board, repos, branch, thresholds, matriz de risco) é
  parametrizável por projeto no setup; o conceitual é agnóstico de harness/projeto.

## Modulação de autonomia (full-agente vs agentes+humanos)
Decidida por **matriz de risco base (template) + limiar configurável (setup)**, e
**RE-CLASSIFICADA continuamente** (não é decisão única no início):
- Matriz base marca como sensível: auth/identidade, migração de dados, pagamento/financeiro,
  mudança multi-repo, infra/secrets/devops. Projeto calibra/estende no setup.
- **Re-risking obrigatório em 4 pontos**: na spec, no plano, no diff (quando o impacto real
  de arquivos/paths fica conhecido) e no pré-merge. Uma tarefa que começa baixo risco e passa
  a tocar classe sensível É RECLASSIFICADA — não pode auto-aprovar trabalho perigoso.
- Classes **hard-sensitive** (auth, pagamento, migração, secrets, infra) têm gate humano
  **NÃO-overridável** pelo agente, independentemente do limiar do projeto.
- O resultado define quantos **checkpoints humanos (✋)** ativam. Baixo risco → full-agente.
- Antes do risco/escopo FINAL, consultar ownership de código/paths impactados (não é spelunking
  de requisito — é detecção de impacto pra classificar com segurança).

## O FLOW (etapas)

🚫 **DoR — Definition of Ready (BLOQUEIO DURO).** Critério definido no setup, documentado em
wiki/git. Checa: ticket refinado, AC presente, dependências resolvidas. Se reprovar, NÃO entra
no flow (é o critério de "pronto pra ser desenvolvido e testado").

**Classificação de risco/complexidade.** Aplica a matriz de risco + limiar do projeto →
define o nível de autonomia (quais ✋ humanos abaixo ficam ativos).

**Grounding (JIT).** Carrega só o contexto relevante à fase. Memória curada como fonte.

**Requisitos na fonte.** Lê o work item (descrição + AC), não spelunking de código.

**Spec + AC testável (QA shift-left).** Spec reconcilia ticket + restrições do repo. QA agent
deriva/critica AC testável (Given-When-Then) + casos de teste. [✋ aprovação humana se risco alto]

**Escopo (FE / BE / FE+BE / mixed).** Decidido aqui, antes de gates dependentes de camada.
Conflito/ambiguidade → `mixed` → união conservadora dos gates + triagem. FE+BE publica
contrato compartilhado autoritativo/versionado antes de paralelizar.

**Plano versionado + juiz de modelo diferente (I1).** Plano com paths/código/ordem TDD.
grill-me-with-codex (modelo diferente) → GO/NO-GO, advisory p/ triagem. [✋ aprovação humana se risco alto]

**Decomposição.** Tarefas curtas e verificáveis. 1 branch `<prefix>/<id>` + worktree por
tarefa. Paralelizar só arquivos disjuntos; senão serial. Contrato compartilhado respeitado.

**Dev loop por tarefa.** implementer (TDD) → spec-review → quality-review → **QA cobertura-vs-AC**.
Git: Conventional Commits c/ ID como scope, pre-commit obrigatório (nunca --no-verify),
verificar git diff origin/base...branch. Teto de retries (I4).

**Gate DoD ortogonal (critério do setup).** Conjunção, introduzida incrementalmente:
held-out tests ISOLADOS (I2, fora da superfície do implementer) + mutation + type/lint/compile
+ contrato + deps (anti-slopsquatting) + **secret scanning de CÓDIGO (bloqueia merge — credencial
no git history já é incidente)** + **SAST para mudança security-relevant** + **E2E real dentro
do gate**. (Provisionamento de secrets/config de INFRA é trilha DevOps de deploy, ver abaixo —
não confundir com secret scanning de código.)

**Review holístico.** Juiz independente (modelo diferente) sobre o codebase + **autoridade de
triagem (I4)**: severidade, determinístico vence advisory só no status factual, teto → escala humano.

**PR + board.** Push, PR com template/título padronizado. Board → Review (adapter Jira/ADO).
[✋ aprovação humana antes do merge se risco alto]

**Merge + board → DEV-DONE.** Board → Done (estado = dev-complete: código entregue, revisado,
provado; NÃO significa em produção). "Entregável ao usuário" só após a trilha de deploy.

**Realimenta memória.** Captura padrão reusável (com curadoria + expiração de lição obsoleta).

**[opt-in deploy — configurável por projeto]** 🔒 **Trilha DevOps de deploy (SEPARADA).** Cobre
provisionamento de secrets/config de INFRA e gates de runtime (não o secret scanning de código,
que já bloqueou no DoD). Achado/pendência de infra → abre TICKET rastreável + bloqueia deploy.
Resolvido → retoma → deploy → health check → rollback automático. Só aqui o estado vira
"entregável ao usuário".

## Governança do DoR/DoD e do template (anti-auto-relaxamento)
- DoR/DoD/matriz de risco são artefatos VERSIONADOS em wiki/git. Mudança exige aprovação humana
  registrada (quem, quando, porquê) — o agente NUNCA relaxa o próprio critério.
- O template define **adapter contracts** explícitos (board, VCS, CI, deploy, notificação) e
  **tiers de capability** (core obrigatório vs opcional). Integrações específicas de projeto
  (ex.: Sodexo ADO/Power Automate) implementam o adapter, sem vazar pro core conceitual.

## Eixos transversais (atravessam todas as etapas)
- **Orquestração:** Claude orquestra; agentes isolados executam.
- **Board adapter:** Jira ou ADO por projeto; transições não-bloqueantes em cada fase.
- **Verificação:** I1 juiz de modelo diferente · I2 oráculo isolado (anti reward-hacking) ·
  I3 done ortogonal · I4 triagem · QA agent (AC testável, cobertura, E2E).
- **Governança:** audit trail (log de decisões/delegações) · token budget por tarefa/story ·
  estado retomável (checkpoint & resume).

## Checkpoints humanos (condicionais ao risco)
1. Spec/AC · 2. Plano (antes de codar) · 3. Antes do merge.
Baixo risco desativa os ✋ (full-agente). DoR é bloqueio automático contra critério do setup.

## Ownership de papéis (sem sobreposição)
- Orquestrador (Claude): estado, decisão, delegação, triagem.
- Implementer: escreve código + testes da tarefa (NÃO é oráculo da própria prova).
- Spec-reviewer / quality-reviewer: corretude e qualidade.
- QA agent: testabilidade da AC + cobertura + E2E (NÃO é o oráculo isolado — isso é I2).
- Juiz externo (modelo diferente): advisory adversarial sobre plano e código.
- Humano: intent/escopo, aprovação nos ✋, resolução de escalations.

## O que NÃO é
Não é rewrite — cada gate é adicionável (1 PR). Subagente é isolamento de contexto, não
fronteira de segurança. DoR/DoD/board/risco são config do projeto, não do conceitual.

## Ordem de adoção (incremental)
1º DoR + DoD do setup (documentados em wiki/git) + matriz de risco. 2º escopo explícito na spec.
3º I4+I1. 4º QA Momento 1 (AC testável). 5º I2 held-out + detecção de edição. 6º QA Momento 2.
7º I3 E2E no gate + QA Momento 3. 8º audit trail + estado retomável. 9º mutation, deps, token
budget, conforme a dor. 10º [opt-in] trilha de deploy + gate DevOps/secrets.

## Artefatos relacionados (onde os detalhes vivem)
- **enforcement-controls-checklist.md** — mecânica REAL dos gates hard-sensitive (separação de
  identidade do agente, config de enforcement imutável, re-risking semântico incluindo
  dependência/config/CI). É o que torna "não-overridável" uma trava, não promessa.
- **repo-architecture.md** — schemas concretos dos adapters, modos dev/serviço, sandbox efêmero,
  aprovação durável headless, deploy conteinerizado, separação admin/runtime.

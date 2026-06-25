# Autonomous SDLC — Modelo e Processo

Documentação de funcionamento da estrutura agêntica autônoma de desenvolvimento de software.
Cobre **todas as etapas do SDLC**, operável como **full-agentes** ou **agentes + humanos**
conforme o risco/complexidade da tarefa. O entregável é um **plugin/template do Claude Code**
que projetos adotam e especializam. Field test de referência: Sodexo.

> Este documento descreve o COMO e o PORQUÊ. Os artefatos normativos detalhados estão em
> [`docs/model/`](model/): o flow, o checklist de enforcement e a arquitetura do repositório.

---

## 1. Princípios fundadores

1. **Claude é o orquestrador; agentes isolados executam.** O orquestrador mantém estado, decide,
   delega e faz triagem — nunca implementa diretamente. Cada subagente roda em contexto isolado;
   o orquestrador repassa explicitamente o que ele precisa (o subagente não herda o histórico).
2. **Um agente nunca é o oráculo da própria prova.** Quem escreve o código não atesta sozinho que
   está correto, coberto e seguro. Verificação é uma **pilha de sinais ortogonais**, e o juiz LLM
   é a camada *advisory* final — nunca a única.
3. **"Mitiga", não "fecha".** Nenhum controle isolado elimina uma classe inteira de risco. A
   segurança vem da combinação de camadas (defesa em profundidade).
4. **É um template.** Tudo específico de um projeto — board (Jira/ADO), repositórios, branches,
   thresholds, matriz de risco, DoR/DoD — é parametrizável no **setup**. O núcleo conceitual é
   agnóstico de harness e de projeto.
5. **Autonomia modulada por risco.** Tarefa de baixo risco roda full-agente; tarefa sensível
   ativa checkpoints humanos. A linha é definida por uma matriz de risco base (no template) +
   limiar configurável (no setup).

---

## 2. O flow do SDLC (visão de uma linha)

DoR (bloqueio duro) → Classificação de risco → Grounding → Requisitos na fonte → Spec + AC
testável (QA shift-left) [✋] → Escopo (FE/BE/mixed) → Plano versionado + juiz de modelo diferente
[✋] → Decomposição (contrato compartilhado; branch + worktree por tarefa) → Dev loop por tarefa
(implementer → spec-review → quality-review → cobertura-vs-AC) → Gate DoD ortogonal (held-out
isolado + mutation + type/lint + contrato + deps + secret-scan + SAST + E2E real) → Review
holístico (juiz independente + triagem) → PR + board [✋ antes do merge] → DEV-DONE → realimenta
memória → [opt-in] trilha DevOps de deploy (secrets/infra → ticket → deploy → health → rollback).

Os ✋ são condicionais ao risco: baixo risco os desativa (full-agente).

---

## 3. As etapas, explicadas

### Definition of Ready (DoR) — bloqueio duro de ENTRADA
Critério, definido no setup e documentado em wiki/git, que decide se algo está **pronto para ser
desenvolvido e testado**: ticket refinado, AC presente, dependências resolvidas. Se reprovar, não
entra no flow. É o portão de entrada — espelha o Definition of Done no portão de saída.

### Classificação de risco — define o nível de autonomia
Aplica a matriz de risco (auth, pagamento, migração, multi-repo, infra/secrets) + o limiar do
projeto. **Re-classificada continuamente** (na spec, no plano, no diff e no pré-merge) — uma
tarefa que começa "baixa" e passa a tocar classe sensível é reclassificada e ganha gate humano.

### Grounding, Requisitos e Spec
Grounding carrega só o contexto relevante à fase (JIT) a partir de memória curada. Requisitos são
lidos na fonte (work item), não por adivinhação no código. A spec **reconcilia** o intent do
ticket com as restrições reais do repo/runtime (contratos, migrations, auth, feature flags).

### QA shift-left — AC testável desde o BA
Um **agente de QA** participa em três momentos, como papel distinto do implementer e do juiz:
1. **BA:** deriva AC testável (Given-When-Then) + casos de teste antes do código.
2. **Code review:** verifica cobertura vs AC (cada AC tem teste? o teste prova a AC?).
3. **E2E:** dirige a validação de fluxo conforme o escopo.
QA cuida de testabilidade; BA/produto cuida de intent; o oráculo isolado é responsabilidade do
gate (não do QA).

### Escopo (FE / BE / FE+BE / mixed)
Decidido cedo, porque define quais gates e qual validação de fluxo rodam. Ambiguidade →
`mixed` → união conservadora dos gates + triagem. FE+BE publica um contrato compartilhado
autoritativo e versionado antes de paralelizar, com drift-check no merge.

### Plano + juiz de modelo diferente
O plano é um artefato versionado. Um **juiz de modelo diferente** (família distinta da que
escreveu) grelha o plano adversarialmente — GO/NO-GO. O autor não corrige a própria prova.

### Decomposição + dev loop
Tarefas curtas e verificáveis, uma branch + worktree por tarefa (isolamento físico). Cada tarefa:
implementer (TDD) → spec-review → quality-review → cobertura-vs-AC, com teto de retries.

### Gate DoD ortogonal — como medimos "done"
"Done" nunca é um único teste verde. É a conjunção: held-out tests **isolados** (fora do alcance
do implementer, contra reward-hacking) + mutation + type/lint/compile + contrato + deps
(anti-slopsquatting) + secret-scan de código + SAST + E2E real. Introduzido incrementalmente.

### Review holístico + triagem
Juiz independente sobre o codebase inteiro; a **autoridade de triagem** classifica severidade,
faz o gate determinístico vencer o advisory no status factual, e escala ao humano quando estoura
o teto. Evita churn infinito de correção.

### PR, DEV-DONE e deploy
PR com template padronizado, board → Review, merge (com ✋ se risco alto) → **DEV-DONE**
(dev-complete ≠ produção). A trilha de deploy é **opt-in por projeto**: secrets/config de infra
viram ticket que bloqueia o deploy; quando resolvido, deploy → health check → rollback automático.

---

## 4. As quatro intervenções de verificação (I1–I4)

| # | Intervenção | O que faz |
|---|---|---|
| I1 | Juiz de modelo diferente | Revisor adversarial de família distinta; advisory na triagem. |
| I2 | Oráculo de teste isolado | Held-out tests fora do alcance do agente + detecção de edição de teste + mutation. Mitiga *reward hacking*. |
| I3 | "Done" ortogonal | Pilha de gates independentes; E2E real dentro do gate. |
| I4 | Autoridade de triagem | Severidade, conflito advisory×determinístico, teto de retries → escala humano. |

---

## 5. Enforcement: por que "não-overridável" é uma trava, não uma promessa

Um agente autônomo só é seguro se não puder contornar os próprios gates. Três princípios
(detalhados em [`docs/model/enforcement-controls-checklist.md`](model/enforcement-controls-checklist.md)):

- **Separação de identidade:** o token do agente tem permissão mínima — não administra branch
  protection, não aprova PR, não escreve secrets, não dá push em branch protegida.
- **Config de enforcement imutável pelo agente:** workflows de CI, CODEOWNERS, scanners,
  thresholds e a matriz de risco vivem em org/server policy protegida; o agente não os edita.
- **Re-risking semântico:** detecta capacidade sensível introduzida (crypto, auth, migração,
  pagamento, secret IO) por análise do diff, onde quer que o código esteja — não confia no label
  que o próprio agente escreveu.

Enforcement em 4 camadas (defesa em profundidade): local (pre-commit) → CI (required checks) →
merge protection (branch protegida/CODEOWNERS) → CD (deploy). A trava real é server-side.

---

## 6. Como o template é entregue e operado

Detalhes em [`docs/model/repo-architecture.md`](model/repo-architecture.md). Em resumo:

- **Dois modos, um core:** o mesmo pipeline roda como (a) **modo dev** — o dev dispara um comando
  do plugin Claude Code, interativo; e (b) **modo serviço** — um webhook do board dispara o
  pipeline headless, sem humano presente.
- **Modo serviço:** webhook ingester (assinatura, idempotência, lock) → fila durável → worker em
  **sandbox efêmero por job** (1 job = 1 container descartável, blast-radius contido). Checkpoints
  humanos viram um **serviço de aprovação durável** (pausa/retoma, identidade + política do
  aprovador, timeout/escalation).
- **Admin separado do runtime:** materializar enforcement e criar a identidade do agente são
  operações de admin, num caminho com credencial humana, inacessível ao worker.
- **Deploy:** conteinerizado na cloud (ingester stateless + worker efêmero + fila gerenciada +
  vault). Um projeto pode rodar só o modo dev, ou o stack completo.

---

## 7. Adoção incremental

Cada peça é adicionável como um PR isolado — não é um big-bang:

1. Core + modo dev (entrega valor sem infra).
2. Enforcement materializado pelo admin path.
3. Adapters de board/VCS.
4. Serviço de aprovação durável.
5. Ingester + fila + worker efêmero (modo serviço).
6. Deploy cloud.
7. Observabilidade (audit trail, token budget, trace correlation).
8. Field test no projeto real (ex.: Sodexo, via adapters ADO).

---

## 8. Glossário rápido

- **DoR / DoD** — Definition of Ready (gate de entrada) / Definition of Done (gate de saída),
  ambos definidos no setup e versionados em wiki/git.
- **Held-out tests** — testes que o agente implementer não vê nem edita; rodados pela CI.
- **Reward hacking** — agente enfraquecer/editar os próprios testes pra passar.
- **Juiz de modelo diferente** — revisor adversarial de família de modelo distinta do autor.
- **Sandbox efêmero** — container descartável, um por job, destruído ao fim.

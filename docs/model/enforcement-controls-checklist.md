# Controles de Enforcement — Checklist do Setup do Projeto

Parte do template SDLC autônomo. Resolve o Minor 1 dos juízes: gates "não-overridáveis"
(auth/pagamento/migração/secrets/infra) NÃO podem ser só política do orquestrador — têm que
ser TRAVAS REAIS que o agente não consegue burlar. Configurado no **setup do plugin por projeto**.

## Princípio nº0 — SEPARAÇÃO DE IDENTIDADE (a base de tudo)
Sem isto, todo o resto é teatro. A **identidade/token do agente autônomo** é distinta da do
humano e tem permissão MÍNIMA. O token do agente NÃO PODE:
- administrar/alterar branch protection, rulesets, required checks ou environments;
- aprovar PRs, dispensar (dismiss) reviews, ou marcar como "bypass";
- dar push em branch protegida; escrever secrets/variáveis protegidas;
- editar os arquivos que DEFINEM o enforcement (ver Princípio nº1).
"Human approval" e "non-overridable" só são reais porque o token do agente é incapaz de
contorná-los — é trava de identidade, não promessa de comportamento.

## Princípio nº1 — A CONFIG DE ENFORCEMENT É IMUTÁVEL PELO AGENTE
De nada adianta um required check se o agente edita o arquivo que o define mantendo o nome.
Arquivos que DEFINEM enforcement são protegidos por **org/server policy (rulesets centralizados,
reusable required workflows)** — não apenas CODEOWNERS de repo — e o agente **não pode aprovar
nem alterar a própria ownership**:
- workflows de CI/CD, configs de scanner (SAST/SCA/secret/PII), thresholds (cobertura/mutation),
- CODEOWNERS, branch-protection/ruleset config, matriz de risco, lockfiles, pre-commit config,
- invocação/fixtures/wiring dos held-out tests.
- **registro de regras de capacidade sensível** (mapeia cada capacidade → grupo de owner humano);
  mantido por humano, com **revisão periódica de falsos-negativos** (regra nova quando um padrão
  sensível escapou). É o que alimenta o re-risking semântico (Cam.2).
Fonte de verdade do enforcement = **org/server policy protegida**, não doc no repo (o repo só
documenta/rastreia). Mudança nesses arquivos exige review de owner humano (token do agente não aprova).

## Princípio nº2 — Defesa em profundidade
O mesmo risco é checado em camadas (local → CI → merge → CD). Hook local é ergonomia (o agente
pode pular); a trava REAL é server-side.

---

## Camada 1 — Local (pre-commit)  [ergonomia; redundar sempre na CI]
- [ ] Secret scanning (detect-secrets/gitleaks/TruffleHog). CORE (real na Cam.2)
- [ ] PII detector (CPF/email/cartão/dados pessoais). CORE (real na Cam.2)
- [ ] Lint + format; type-check/compile. CORE
- [ ] Conventional Commits + branch naming validator. CORE
> `--no-verify` é burlável localmente → não é controle; o controle real é o required check server-side.

## Camada 2 — CI (required checks server-side, enforçados de fora do repo)
- [ ] Secret scanning. CORE
- [ ] PII scan. CORE
- [ ] **Re-risking check INDEPENDENTE do agente (semântico + path + ownership)**: NÃO confia em
      label/descrição do agente. Combina (a) **detecção semântica de CAPACIDADE sensível
      introduzida** onde quer que esteja — novo uso de crypto/assinatura, manipulação de
      token/sessão/auth, SQL de migração/DDL, chamada a gateway de pagamento, leitura/escrita de
      secret, syscalls de infra — via análise do diff (AST/regras), não só nome de path; (b)
      detecção por path sensível; (c) mudança de dependência/config/CI. Se o agente realocar
      comportamento sensível p/ path não-classificado, (a) ainda dispara o gate. Owner humano da
      capacidade sensível é exigido independentemente de onde o código mora. **Fail-closed:**
      artefatos gerados/minified/binários, código vendored, e uso de eval dinâmico/reflection que
      a análise não consegue inspecionar → bloqueiam ou exigem review humano (não passam por
      omissão). CORE
- [ ] SAST. CORE
- [ ] SCA/dependency (CVE HIGH/CRITICAL falha; anti-slopsquatting: registro+lockfile pin+
      allowlist+bloqueio de install-scripts). **Adição de dependência que toca domínio sensível
      (crypto/auth/pagamento/rede/infra) → review de owner humano**, não só SCA/license. CORE
- [ ] Suíte completa + cobertura mínima. CORE
- [ ] **Held-out/secret tests** — invocação/fixtures PROTEGIDOS (workflow imutável/human-owned;
      fora da superfície do agente). CORE
- [ ] Mutation (score mínimo, escopo+baseline). OPCIONAL
- [ ] Contrato/OpenAPI validation (drift FE↔BE). CORE p/ BE
- [ ] Container/image scan (Trivy) — **CORE quando há build de imagem**.
- [ ] SBOM generation. CORE (supply-chain é concern declarado)
- [ ] License compliance. OPCIONAL

## Camada 3 — Merge protection (o "não-overridável" real)
- [ ] Required status checks (todos CORE da Cam.2 verdes). CORE
- [ ] Branch protection nas bases (sem push direto, PR obrigatório). CORE
- [ ] CODEOWNERS — classes hard-sensitive exigem owner HUMANO; agente não conta. CORE
- [ ] **CODEOWNERS coverage audit** (check que falha se área sensível ficar sem owner). CORE
- [ ] Required human approval p/ tarefa reclassificada hard-sensitive. CORE
- [ ] **PR template com check que VALIDA campos obrigatórios** (AC, testes, riscos, disclosure).
      Garante que os campos EXISTEM, não a veracidade — NÃO conta como evidência de risco; o
      sinal de risco real vem do re-risking semântico independente (Cam.2). CORE
- [ ] Signed commits/tags (provenance; SLSA/in-toto). CORE (supply-chain)
- [ ] Linear history / no force-push nas bases. OPCIONAL

## Camada 4 — CD/deploy (opt-in; bloqueia DEPLOY, não dev)
- [ ] Provisionamento de secrets/config de INFRA via vault — pendência → ticket. CORE-se-deploy
- [ ] Migração backward-compatible check (Blue-Green; no NOT NULL sem default). CORE-se-deploy
- [ ] **DAST** — CORE-se-deploy p/ classes sensíveis (pagamento/auth); senão opcional.
- [ ] Health check (`/health/ready`→200) + rollback automático. CORE-se-deploy
- [ ] Artifact provenance/signature verify antes de promover. CORE-se-deploy (supply-chain)

---

## Mapeamento risco → enforcement (sem contradição com as camadas)
| Classe | Enforcement obrigatório |
|---|---|
| Auth/identidade | CODEOWNERS+human approval+SAST; DAST no deploy |
| Pagamento | CODEOWNERS+human approval+held-out tests; DAST CORE-se-deploy |
| Migração de dados | human approval + backward-compat (CD) |
| Secrets (código) | secret scanning Cam.1+2 (bloqueia merge) |
| Secrets/infra | vault provisioning (CD; bloqueia deploy via ticket) |
| Multi-repo | contrato compartilhado + drift check + merge ordenado |
| PII | PII detector Cam.1+2 |

## Como o setup do plugin usa isto
1. TEMPLATE entrega a lista + matriz de risco base + esqueletos (pre-commit, PR template,
   CODEOWNERS, workflows, **reusable required workflows centralizados**) como defaults.
2. Setup: projeto escolhe board/stacks/thresholds, calibra risco/limiar, e **cria a identidade
   do agente com permissão mínima** (Princípio nº0).
3. Setup **materializa** os controles E configura branch protection / required checks / rulesets
   via API do VCS — com a config de enforcement protegida por CODEOWNERS/org policy (Princípio nº1).
4. Documentado em wiki/git p/ rastreio; a fonte de verdade do enforcement é a org policy protegida.

## Adapter de VCS (schema concreto — Minor 2) precisa expor
`set_branch_protection`, `set_required_checks`, `set_codeowners`, `set_pr_template`,
`create_scoped_agent_identity(permissions)`, `protect_paths(globs, owners)`.

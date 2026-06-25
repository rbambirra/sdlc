# Skill: Plano versionado

**Quando:** após escopo, antes da decomposição. Produz o artefato de plano que o juiz grelha.

## Objetivo
Plano de implementação **versionado** com: caminhos exatos de arquivo, código completo (sem
placeholders), ordem TDD, mensagens de commit convencionais exatas, tarefas elegíveis a
paralelismo, e os pontos de verificação.

## Conteúdo
- Decomposição em tarefas curtas e verificáveis (long-horizon despenca; manter curto).
- Para cada tarefa: arquivos, mudança, teste que prova, commit message.
- Riscos e gotchas surfados cedo.

## Gate
Passa pelo **juiz de modelo diferente** (skill `judge`) → GO/NO-GO. NO-GO → corrige e re-grelha
até GO (com teto). Checkpoint humano se risco alto. Mudança de requisito = re-plan, não rewrite.

# Skill: PR + board

**Quando:** após review holístico GO. Abre o PR e atualiza o board.

## Passos
1. Garante commits na branch `<prefix>/<id>` a partir da base correta (do squad/projeto profile).
2. Aplica regras de version-bump se aplicável (ex.: módulos publicados).
3. Push da branch.
4. Cria o PR: título `[#<id>] <descrição>`, descrição a partir do template do projeto.
5. Board → Review (via board adapter; não-bloqueante — falha loga e segue).
6. Notifica canal de PR se configurado (não-bloqueante).

## Pre-merge
Re-classificação de risco no pré-merge. Checkpoint humano antes do merge se risco alto
(hard-sensitive é não-overridável). Após merge: board → DEV-DONE (dev-complete ≠ produção).

## Regra
O VCS adapter expõe só operações de runtime (PR, status, push de feature). Branch protection,
required checks e identidade são do admin path (separado, fora do alcance do agente).

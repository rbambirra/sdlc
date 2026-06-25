# Skill: Dev loop por tarefa

**Quando:** para cada tarefa da decomposição. Isolamento físico: 1 branch + 1 worktree por tarefa.

## Ciclo
1. **Implementer** (subagente, TDD) — implementa a tarefa. NÃO é dono do oráculo da própria prova.
2. **Spec-review** — código vs spec compliance (não fez mais nem menos).
3. **Quality-review** — qualidade de código.
4. **QA cobertura-vs-AC** — cada AC tem teste? edge cases? o teste prova a AC ou só passa?

## Regras de git (do CLAUDE.md/AGENTS.md do projeto)
- Branch `<prefix>/<id>` (feat/fix/refact/chore por tipo de work item).
- Conventional Commits com o ID como scope: `feat(123): add X`.
- Pre-commit hooks obrigatórios — **nunca `--no-verify`**.
- Verificar `git diff origin/<base>...<branch>` — passar teste não prova a mudança.

## Limites
Teto de retries por tarefa (não "fix até GO" infinito). Estourou → escala humano (triagem).
Paralelizar só tarefas com arquivos disjuntos; senão serial.

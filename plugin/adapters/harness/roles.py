"""Shared role taxonomy for harness adapters.

The pipeline dispatches tasks tagged with a role. Two execution modes follow:

- BUILDER roles materialize code on disk: they run inside an ISOLATED worktree
  and actually write/run code. The worktree is the deliverable side-effect.
- ANALYTIC roles produce an artifact as TEXT (spec, plan, review, qa, judge).
  They read and answer; they must not need to write files.

Kept in one place so every adapter (Claude, Codex, future harnesses) agrees on
which roles build vs. analyze, instead of each redefining the set.
"""
from __future__ import annotations

# Roles that write code to disk. Everything else is analytic (text artifact).
BUILDER_ROLES = {"implementer"}

# Analytic roles that nonetheless READ code (the worktree/impl) before answering
# — they need a few tool turns more than pure text roles. The fake_scenario
# showed quality_reviewer starving at the flat analytic budget.
CODE_READING_ROLES = {"spec_reviewer", "quality_reviewer", "qa"}

# Context budget per role kind. Builders must see the FULL plan (truncating it
# makes the implementer code blind and drift off-task — observed in the
# fake_scenario when Codex, fed a 500-char plan slice, built the wrong thing).
# Analytic roles keep a cap to avoid runaway prompts.
ANALYTIC_CTX_CHARS = 500
BUILDER_CTX_CHARS = 8000

# Turn budgets (for harnesses that meter turns, e.g. Claude). Pure text roles
# answer in a couple of turns; code-reading reviewers need to inspect first;
# builders iterate heavily.
TEXT_MAX_TURNS = 6
REVIEW_MAX_TURNS = 15
BUILDER_MAX_TURNS = 40


def is_builder(role: str) -> bool:
    return role in BUILDER_ROLES


def turn_budget(role: str) -> int:
    """Max agent turns for a role, for harnesses that meter turns."""
    if role in BUILDER_ROLES:
        return BUILDER_MAX_TURNS
    if role in CODE_READING_ROLES:
        return REVIEW_MAX_TURNS
    return TEXT_MAX_TURNS


def render_context(task_context: dict, role: str) -> str:
    """Render task.context as prompt lines, with a per-role char budget so the
    builder sees the full plan while analytic roles stay bounded."""
    cap = BUILDER_CTX_CHARS if is_builder(role) else ANALYTIC_CTX_CHARS
    return "\n".join(f"- {k}: {str(v)[:cap]}" for k, v in task_context.items())

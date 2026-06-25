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

# Context budget per role kind. Builders must see the FULL plan (truncating it
# makes the implementer code blind and drift off-task — observed in the
# fake_scenario when Codex, fed a 500-char plan slice, built the wrong thing).
# Analytic roles keep a cap to avoid runaway prompts.
ANALYTIC_CTX_CHARS = 500
BUILDER_CTX_CHARS = 8000


def is_builder(role: str) -> bool:
    return role in BUILDER_ROLES


def render_context(task_context: dict, role: str) -> str:
    """Render task.context as prompt lines, with a per-role char budget so the
    builder sees the full plan while analytic roles stay bounded."""
    cap = BUILDER_CTX_CHARS if is_builder(role) else ANALYTIC_CTX_CHARS
    return "\n".join(f"- {k}: {str(v)[:cap]}" for k, v in task_context.items())

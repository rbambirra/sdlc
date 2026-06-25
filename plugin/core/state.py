"""
state.py — resumable pipeline state (checkpoint & resume).

The orchestrator persists a PipelineState after each phase so a job that dies
(worker crash, restart) can resume from where it left off instead of redoing
work. Job IDs are canonical (derived from the board event) so resume is
idempotent: re-running a job does not duplicate a PR already created.

MVP: JSON file persistence. Cloud mode swaps the store via the same interface.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Phase(Enum):
    DOR = "dor"
    RISK = "risk"
    GROUNDING = "grounding"
    REQUIREMENTS = "requirements"
    SPEC = "spec"
    SCOPE = "scope"
    PLAN = "plan"
    DECOMPOSE = "decompose"
    DEVLOOP = "devloop"
    DOD_GATE = "dod_gate"
    REVIEW = "review"
    PR = "pr"
    DONE = "done"


@dataclass
class PipelineState:
    job_id: str                      # canonical, derived from board event-id
    work_item_id: str
    phase: str = Phase.DOR.value
    completed_phases: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)   # spec, plan, scope, pr_ref...
    blocked: bool = False
    block_reason: str = ""

    def advance(self, phase: Phase) -> None:
        if self.phase not in self.completed_phases:
            self.completed_phases.append(self.phase)
        self.phase = phase.value

    def has_completed(self, phase: Phase) -> bool:
        return phase.value in self.completed_phases


class StateStore:
    """JSON-file state store. Idempotent: same job_id -> same file."""

    def __init__(self, root: str | None = None):
        self.root = root or os.path.join(tempfile.gettempdir(), "sdlc-state")
        os.makedirs(self.root, exist_ok=True)

    def _path(self, job_id: str) -> str:
        safe = job_id.replace("/", "_")
        return os.path.join(self.root, f"{safe}.json")

    def load(self, job_id: str) -> PipelineState | None:
        p = self._path(job_id)
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as fh:
            return PipelineState(**json.load(fh))

    def save(self, state: PipelineState) -> None:
        p = self._path(state.job_id)
        # atomic write: temp + rename (no half-written state on crash)
        fd, tmp = tempfile.mkstemp(dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(asdict(state), fh, indent=2)
            os.replace(tmp, p)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def load_or_create(self, job_id: str, work_item_id: str) -> PipelineState:
        return self.load(job_id) or PipelineState(job_id=job_id, work_item_id=work_item_id)

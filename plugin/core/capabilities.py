"""
capabilities.py — The portability seam.

The core orchestrator speaks ONLY in these abstract capabilities. It never
imports a harness SDK, never knows whether it is running on Claude, Codex,
Hermes, or a mock. Each harness ships a thin adapter implementing `Harness`;
each board/VCS provider ships an adapter implementing `Board` / `Vcs`.

This is the contract every adapter must honor (and the conformance suite in
tests/ verifies it). Keep adapters thin: logic lives in the core, the adapter
only translates this contract to a native primitive.

Python 3.11+. Stdlib only.
"""
from __future__ import annotations

import enum
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol


# --------------------------------------------------------------------------
# Job / dispatch semantics (async by contract — never block the orchestrator)
# --------------------------------------------------------------------------
class JobStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class FailureKind(enum.Enum):
    """Every failure distinguishes transient (retry) from terminal (escalate)."""
    NONE = "none"
    TRANSIENT = "transient"   # retry with backoff
    TERMINAL = "terminal"     # do not retry; escalate to triage/human


@dataclass
class Usage:
    """Cost/token reporting. Adapters fill what they can; zeros if unknown."""
    input_tokens: int = 0
    output_tokens: int = 0
    usd: float = 0.0


@dataclass
class Task:
    """A unit of work handed to a subagent. Context is passed EXPLICITLY —
    the subagent never inherits the orchestrator's history."""
    role: str                       # implementer | spec_reviewer | quality_reviewer | qa | judge ...
    instructions: str               # the prompt / skill body for this task
    context: dict[str, Any] = field(default_factory=dict)  # files, AC, plan slice...
    model_hint: str | None = None   # suggestion; adapter may map or ignore
    timeout_s: float | None = None
    allowlist: list[str] = field(default_factory=list)     # tools this role may use


@dataclass
class JobResult:
    status: JobStatus
    output: str = ""
    error: str = ""
    failure_kind: FailureKind = FailureKind.NONE
    usage: Usage = field(default_factory=Usage)


class JobHandle(ABC):
    """Async handle to a dispatched subagent. The core polls / waits / cancels."""
    job_id: str

    @abstractmethod
    def status(self) -> JobStatus: ...

    @abstractmethod
    def result(self) -> JobResult:
        """Blocks only if you choose to; returns current result snapshot."""

    @abstractmethod
    def cancel(self) -> None:
        """Best-effort cancellation; status becomes CANCELLED."""

    def wait(self, poll_s: float = 0.05, timeout_s: float | None = None) -> JobResult:
        """Convenience: poll until terminal state or timeout."""
        start = time.monotonic()
        terminal = {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.TIMED_OUT}
        while self.status() not in terminal:
            if timeout_s is not None and (time.monotonic() - start) > timeout_s:
                self.cancel()
                return JobResult(status=JobStatus.TIMED_OUT,
                                 failure_kind=FailureKind.TRANSIENT,
                                 error="wait timeout")
            time.sleep(poll_s)
        return self.result()


# --------------------------------------------------------------------------
# Gate semantics (deterministic verification; held-out tests run HERE)
# --------------------------------------------------------------------------
@dataclass
class Finding:
    severity: str   # block | major | minor
    message: str
    location: str = ""


@dataclass
class GateResult:
    passed: bool
    findings: list[Finding] = field(default_factory=list)
    failure_kind: FailureKind = FailureKind.NONE


# --------------------------------------------------------------------------
# Approval semantics (durable pause/resume; first-class for headless mode)
# --------------------------------------------------------------------------
class ApprovalState(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    EDITED = "edited"      # approver changed the artifact; core must re-validate


@dataclass
class Checkpoint:
    name: str                       # spec | plan | pre_merge | hard_sensitive ...
    summary: str
    artifact_ref: str = ""          # what is being approved
    required_policy: str = ""       # who may approve (e.g. "codeowner:auth")


@dataclass
class ApprovalRecord:
    checkpoint: str
    state: ApprovalState
    approver: str = ""
    decided_at: float = 0.0
    note: str = ""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))


# --------------------------------------------------------------------------
# The three protocols every integration implements
# --------------------------------------------------------------------------
class Harness(Protocol):
    """A coding-agent harness (Claude Code, Codex, Hermes, mock)."""
    name: str

    def dispatch_subagent(self, task: Task) -> JobHandle:
        """Async dispatch. Returns immediately with a handle. Never blocks."""
        ...

    def run_gate(self, name: str, inputs: dict[str, Any]) -> GateResult:
        """Run a deterministic gate (tests, lint, scanner...). Idempotent.
        Held-out/secret tests run here — NOT inside the implementer subagent."""
        ...

    def request_approval(self, checkpoint: Checkpoint) -> ApprovalRecord:
        """Durable pause/resume. Persists an ApprovalRecord; blocks the JOB
        (not the whole orchestrator) until a terminal ApprovalState."""
        ...


class Board(Protocol):
    """Work-tracking board (Jira / ADO / mock)."""
    name: str

    def get_work_item(self, item_id: str) -> dict[str, Any]: ...
    def transition(self, item_id: str, state: str) -> None: ...        # non-blocking; log on fail
    def comment(self, item_id: str, body: str) -> None: ...
    def create_ticket(self, title: str, body: str, kind: str) -> str: ...


class Vcs(Protocol):
    """Version control (GitHub / ADO Repos / mock). RUNTIME ops only —
    NEVER branch protection / identity / required-checks admin (that is the
    separate admin/ bootstrap path, unavailable to the agent)."""
    name: str

    def open_pr(self, branch: str, base: str, title: str, body: str) -> str: ...
    def get_checks_status(self, pr_ref: str) -> dict[str, str]: ...
    def push_branch(self, branch: str) -> None: ...

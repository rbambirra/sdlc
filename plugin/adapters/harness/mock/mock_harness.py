"""
mock harness — in-process reference adapter.

Implements the full capabilities.Harness contract synchronously-but-async-shaped
(runs the "subagent" via a user-supplied callable). Used by the conformance
suite and the pipeline smoke test. Deterministic, no network, no real model.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable

from core.capabilities import (
    ApprovalRecord,
    ApprovalState,
    Board,
    Checkpoint,
    FailureKind,
    Finding,
    GateResult,
    Harness,
    JobHandle,
    JobResult,
    JobStatus,
    Task,
    Usage,
    Vcs,
)

# A "brain" decides what a dispatched task returns. Tests inject their own.
Brain = Callable[[Task], JobResult]
GateFn = Callable[[str, dict[str, Any]], GateResult]
ApprovalFn = Callable[[Checkpoint], ApprovalRecord]


class _MockJob(JobHandle):
    def __init__(self, task: Task, brain: Brain):
        self.job_id = f"mock-{id(self)}"
        self._task = task
        self._brain = brain
        self._status = JobStatus.PENDING
        self._result: JobResult | None = None
        self._cancelled = False
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        with self._lock:
            if self._cancelled:
                return
            self._status = JobStatus.RUNNING
        try:
            res = self._brain(self._task)
        except Exception as exc:  # adapter surfaces brain errors as terminal
            res = JobResult(status=JobStatus.FAILED, error=str(exc),
                            failure_kind=FailureKind.TERMINAL)
        with self._lock:
            if self._cancelled:
                return
            self._result = res
            self._status = res.status

    def status(self) -> JobStatus:
        with self._lock:
            return self._status

    def result(self) -> JobResult:
        with self._lock:
            if self._result is not None:
                return self._result
            if self._cancelled:
                return JobResult(status=JobStatus.CANCELLED, failure_kind=FailureKind.TERMINAL)
            return JobResult(status=self._status)

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            self._status = JobStatus.CANCELLED


class MockHarness(Harness):
    name = "mock"

    def __init__(self, brain: Brain | None = None,
                 gate_fn: GateFn | None = None,
                 approval_fn: ApprovalFn | None = None):
        self._brain = brain or self._default_brain
        self._gate_fn = gate_fn or self._default_gate
        self._approval_fn = approval_fn or self._default_approval

    @staticmethod
    def _default_brain(task: Task) -> JobResult:
        return JobResult(status=JobStatus.DONE, output=f"[{task.role}] ok",
                         usage=Usage(input_tokens=10, output_tokens=5))

    @staticmethod
    def _default_gate(name: str, inputs: dict[str, Any]) -> GateResult:
        return GateResult(passed=True)

    @staticmethod
    def _default_approval(cp: Checkpoint) -> ApprovalRecord:
        return ApprovalRecord(checkpoint=cp.name, state=ApprovalState.APPROVED,
                              approver="mock-approver", decided_at=time.time())

    def dispatch_subagent(self, task: Task) -> JobHandle:
        return _MockJob(task, self._brain)

    def run_gate(self, name: str, inputs: dict[str, Any]) -> GateResult:
        return self._gate_fn(name, inputs)

    def request_approval(self, checkpoint: Checkpoint) -> ApprovalRecord:
        return self._approval_fn(checkpoint)


class MockBoard(Board):
    name = "mock"

    def __init__(self) -> None:
        self.log: list[str] = []
        self._items: dict[str, dict[str, Any]] = {
            "DEMO-1": {
                "id": "DEMO-1",
                "title": "Add site selector to dashboard",
                "type": "User Story",
                "description": "As an operator I want to pick a site.",
                "acceptance_criteria": [
                    "Given the dashboard, when I open the selector, then I see my sites.",
                    "Given no site, then a friendly empty state shows.",
                ],
                "state": "Ready",
            }
        }
        self._seq = 100

    def get_work_item(self, item_id: str) -> dict[str, Any]:
        return self._items.get(item_id, {"id": item_id, "title": "(unknown)", "acceptance_criteria": []})

    def transition(self, item_id: str, state: str) -> None:
        self.log.append(f"transition {item_id} -> {state}")
        if item_id in self._items:
            self._items[item_id]["state"] = state

    def comment(self, item_id: str, body: str) -> None:
        self.log.append(f"comment {item_id}: {body[:40]}")

    def create_ticket(self, title: str, body: str, kind: str) -> str:
        self._seq += 1
        tid = f"DEMO-{self._seq}"
        self.log.append(f"create_ticket {tid} [{kind}] {title[:30]}")
        return tid


class MockVcs(Vcs):
    name = "mock"

    def __init__(self) -> None:
        self.log: list[str] = []
        self._pr_seq = 0

    def open_pr(self, branch: str, base: str, title: str, body: str) -> str:
        self._pr_seq += 1
        ref = f"PR-{self._pr_seq}"
        self.log.append(f"open_pr {ref} {branch}->{base} {title[:30]}")
        return ref

    def get_checks_status(self, pr_ref: str) -> dict[str, str]:
        return {"required": "success"}

    def push_branch(self, branch: str) -> None:
        self.log.append(f"push {branch}")

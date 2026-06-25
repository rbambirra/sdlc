"""
cli_base.py — shared base for harness adapters that drive a CLI subprocess.

Real async: dispatch spawns the CLI in a background thread, returns a JobHandle
immediately, and the core polls/waits/cancels. Claude and Codex adapters only
differ in how they build the argv and parse output — the lifecycle is here.

Keep adapters thin: this base holds the async/cancel/timeout machinery so each
adapter is just argv construction + output parsing.
"""
from __future__ import annotations

import subprocess
import threading
import time
from typing import Callable

from core.capabilities import (
    ApprovalRecord,
    ApprovalState,
    Checkpoint,
    FailureKind,
    GateResult,
    JobHandle,
    JobResult,
    JobStatus,
    Task,
    Usage,
)


class _CliJob(JobHandle):
    """Runs argv in a background thread; non-blocking handle."""

    def __init__(self, argv: list[str], parse: Callable[[str], str],
                 timeout_s: float | None):
        self.job_id = f"cli-{id(self)}"
        self._argv = argv
        self._parse = parse
        self._timeout = timeout_s
        self._proc: subprocess.Popen | None = None
        self._status = JobStatus.PENDING
        self._result: JobResult | None = None
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        with self._lock:
            self._status = JobStatus.RUNNING
        try:
            self._proc = subprocess.Popen(
                self._argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                out, _ = self._proc.communicate(timeout=self._timeout)
                rc = self._proc.returncode
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.communicate()
                with self._lock:
                    if self._status != JobStatus.CANCELLED:
                        self._result = JobResult(status=JobStatus.TIMED_OUT,
                                                 failure_kind=FailureKind.TRANSIENT,
                                                 error="cli timeout")
                        self._status = JobStatus.TIMED_OUT
                return

            with self._lock:
                if self._status == JobStatus.CANCELLED:
                    return
                if rc == 0:
                    self._result = JobResult(status=JobStatus.DONE,
                                             output=self._parse(out),
                                             usage=Usage())
                    self._status = JobStatus.DONE
                else:
                    # non-zero exit: treat as transient (CLI/proxy hiccup) so the
                    # core can retry; persistent failures escalate via retry cap.
                    self._result = JobResult(status=JobStatus.FAILED,
                                             error=out[-500:],
                                             failure_kind=FailureKind.TRANSIENT)
                    self._status = JobStatus.FAILED
        except Exception as exc:  # spawn failure etc. -> terminal
            with self._lock:
                if self._status != JobStatus.CANCELLED:
                    self._result = JobResult(status=JobStatus.FAILED, error=str(exc),
                                             failure_kind=FailureKind.TERMINAL)
                    self._status = JobStatus.FAILED

    def status(self) -> JobStatus:
        with self._lock:
            return self._status

    def result(self) -> JobResult:
        with self._lock:
            if self._result is not None:
                return self._result
            return JobResult(status=self._status)

    def cancel(self) -> None:
        with self._lock:
            self._status = JobStatus.CANCELLED
            if self._proc and self._proc.poll() is None:
                self._proc.kill()


class _FailedJob(JobHandle):
    """A handle that is already terminally failed (e.g. argv build failed)."""

    def __init__(self, error: str):
        self.job_id = f"failed-{id(self)}"
        self._error = error

    def status(self) -> JobStatus:
        return JobStatus.FAILED

    def result(self) -> JobResult:
        return JobResult(status=JobStatus.FAILED, error=self._error,
                         failure_kind=FailureKind.TERMINAL)

    def cancel(self) -> None:
        pass


class CliHarnessBase:
    """Base impl of the Harness contract over a CLI. Subclass sets `name` and
    overrides `_build_argv` / `_parse_output`. Gates and approvals are pluggable
    (default: gates pass, approvals auto-approve) so the core is testable; real
    deployments wire real gate runners and a durable approval service."""

    name = "cli-base"
    default_timeout_s = 300.0

    def __init__(self,
                 gate_fn: Callable[[str, dict], GateResult] | None = None,
                 approval_fn: Callable[[Checkpoint], ApprovalRecord] | None = None):
        self._gate_fn = gate_fn or (lambda n, i: GateResult(passed=True))
        self._approval_fn = approval_fn or (
            lambda cp: ApprovalRecord(checkpoint=cp.name, state=ApprovalState.APPROVED,
                                      approver=f"{self.name}-auto", decided_at=time.time()))

    # -- subclass hooks ----------------------------------------------------
    def _build_argv(self, task: Task) -> list[str]:
        raise NotImplementedError

    def _parse_output(self, raw: str) -> str:
        return raw.strip()

    # -- contract ----------------------------------------------------------
    def dispatch_subagent(self, task: Task) -> JobHandle:
        # dispatch must ALWAYS return a JobHandle. If argv construction fails
        # (e.g. CLI unavailable), surface it as a terminal-failed job, not an
        # exception that breaks the orchestrator.
        try:
            argv = self._build_argv(task)
        except Exception as exc:
            return _FailedJob(str(exc))
        return _CliJob(argv, self._parse_output, task.timeout_s or self.default_timeout_s)

    def run_gate(self, name: str, inputs: dict) -> GateResult:
        return self._gate_fn(name, inputs)

    def request_approval(self, checkpoint: Checkpoint) -> ApprovalRecord:
        return self._approval_fn(checkpoint)

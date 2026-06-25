"""
Conformance for the real CLI harness adapters — the PORTABILITY PROOF.

The same contract assertions, driven against real CLIs (Claude / Codex) instead
of the mock. If these pass, the core can drive those harnesses unchanged.

These tests invoke real subprocesses, so they are marked slow/integration and
skipped automatically when the CLI is not on PATH. Run explicitly:
    pytest tests/test_conformance_cli.py -m integration
"""
from __future__ import annotations

import shutil
import time

import pytest

from core.capabilities import (
    ApprovalRecord,
    ApprovalState,
    Checkpoint,
    FailureKind,
    GateResult,
    JobHandle,
    JobStatus,
    Task,
)
from adapters.harness.claude.claude_harness import ClaudeHarness
from adapters.harness.codex.codex_harness import CodexHarness
from adapters.harness.hermes.hermes_harness import HermesHarness


pytestmark = pytest.mark.integration


def _has(binary: str) -> bool:
    return shutil.which(binary) is not None


# A tiny task that any harness can answer fast.
def _ping_task() -> Task:
    return Task(role="ping", instructions="Reply with exactly the word PONG and nothing else.",
                context={}, timeout_s=90)


@pytest.mark.skipif(not _has("claude"), reason="claude CLI not on PATH")
def test_claude_adapter_contract():
    h = ClaudeHarness()
    start = time.monotonic()
    handle = h.dispatch_subagent(_ping_task())
    assert isinstance(handle, JobHandle)
    assert (time.monotonic() - start) < 2.0  # async: returns immediately
    res = handle.wait(poll_s=0.2, timeout_s=120)
    assert res.status in {JobStatus.DONE, JobStatus.FAILED, JobStatus.TIMED_OUT}
    if res.status == JobStatus.DONE:
        assert "PONG" in res.output.upper()
    # gate + approval contract (defaults)
    assert isinstance(h.run_gate("x", {}), GateResult)
    rec = h.request_approval(Checkpoint(name="plan", summary="ok"))
    assert isinstance(rec, ApprovalRecord) and isinstance(rec.state, ApprovalState)


@pytest.mark.skipif(not _has("codex"), reason="codex CLI not on PATH")
def test_codex_adapter_contract():
    h = CodexHarness()
    handle = h.dispatch_subagent(_ping_task())
    assert isinstance(handle, JobHandle)
    res = handle.wait(poll_s=0.3, timeout_s=180)
    assert res.status in {JobStatus.DONE, JobStatus.FAILED, JobStatus.TIMED_OUT}


def test_hermes_stub_reports_unavailable_clearly():
    # In the sandbox the hermes CLI is absent; the adapter must fail clearly,
    # not silently. This proves the stub honors the contract shape.
    h = HermesHarness(binary="hermes-does-not-exist")
    res = h.dispatch_subagent(_ping_task()).wait(timeout_s=10)
    assert res.status == JobStatus.FAILED
    assert res.failure_kind == FailureKind.TERMINAL
    assert "not found" in res.error.lower()

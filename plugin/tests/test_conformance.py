"""
Conformance suite — executable spec every Harness adapter MUST pass to be
"supported". Parametrized over a `harness_factory` fixture; the Hermes/Codex/
Claude adapters reuse this exact suite by overriding the fixture.

This is the proof of portability: the same contract, asserted identically
across different adapters. If an adapter passes this, the core can drive it.

Run: pytest tests/test_conformance.py
"""
from __future__ import annotations

import time

import pytest

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
)
from adapters.harness.mock.mock_harness import MockHarness


# --------------------------------------------------------------------------
# Fixture: the factory under test. Adapters override this to run the suite
# against themselves, e.g. in tests/test_conformance_hermes.py:
#   @pytest.fixture
#   def harness_factory(): return lambda **kw: HermesHarness(**kw)
# --------------------------------------------------------------------------
@pytest.fixture
def harness_factory():
    return lambda **kw: MockHarness(**kw)


def _task(role: str = "implementer") -> Task:
    return Task(role=role, instructions="do the thing", context={"x": 1})


# 1. dispatch is async-shaped: returns a JobHandle immediately ---------------
def test_dispatch_returns_jobhandle_immediately(harness_factory):
    h = harness_factory()
    start = time.monotonic()
    handle = h.dispatch_subagent(_task())
    elapsed = time.monotonic() - start
    assert isinstance(handle, JobHandle)
    assert handle.job_id
    # Returning a handle must not block on the full task duration.
    assert elapsed < 1.0


# 2. wait() reaches a terminal status ---------------------------------------
def test_wait_reaches_terminal(harness_factory):
    h = harness_factory()
    res = h.dispatch_subagent(_task()).wait(timeout_s=5)
    assert isinstance(res, JobResult)
    assert res.status in {
        JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.TIMED_OUT
    }


# 3. cancel() yields CANCELLED ----------------------------------------------
def test_cancel_yields_cancelled(harness_factory):
    # A slow brain so we can cancel before it finishes.
    def slow_brain(task):
        time.sleep(0.5)
        return JobResult(status=JobStatus.DONE, output="late")

    h = harness_factory(brain=slow_brain)
    handle = h.dispatch_subagent(_task())
    handle.cancel()
    assert handle.status() == JobStatus.CANCELLED


# 4. a raising brain -> FAILED + TERMINAL -----------------------------------
def test_raising_brain_is_terminal_failure(harness_factory):
    def boom(task):
        raise RuntimeError("kaboom")

    h = harness_factory(brain=boom)
    res = h.dispatch_subagent(_task()).wait(timeout_s=5)
    assert res.status == JobStatus.FAILED
    assert res.failure_kind == FailureKind.TERMINAL
    assert "kaboom" in res.error


# 5. timeout path -> TIMED_OUT + TRANSIENT ----------------------------------
def test_wait_timeout_is_transient(harness_factory):
    def slow_brain(task):
        time.sleep(2.0)
        return JobResult(status=JobStatus.DONE)

    h = harness_factory(brain=slow_brain)
    res = h.dispatch_subagent(_task()).wait(poll_s=0.02, timeout_s=0.2)
    assert res.status == JobStatus.TIMED_OUT
    assert res.failure_kind == FailureKind.TRANSIENT


# 6. run_gate returns GateResult and is idempotent --------------------------
def test_run_gate_idempotent(harness_factory):
    calls = {"n": 0}

    def gate_fn(name, inputs):
        calls["n"] += 1
        return GateResult(passed=(inputs.get("ok", True)))

    h = harness_factory(gate_fn=gate_fn)
    r1 = h.run_gate("held_out_tests", {"ok": True})
    r2 = h.run_gate("held_out_tests", {"ok": True})
    assert isinstance(r1, GateResult) and isinstance(r2, GateResult)
    assert r1.passed == r2.passed  # same inputs -> same verdict


# 7. request_approval returns a valid ApprovalRecord ------------------------
def test_request_approval_record(harness_factory):
    h = harness_factory()
    rec = h.request_approval(Checkpoint(name="plan", summary="approve the plan"))
    assert isinstance(rec, ApprovalRecord)
    assert isinstance(rec.state, ApprovalState)
    assert rec.record_id
    assert rec.checkpoint == "plan"


# 7b. approval state machine: rejection is honored --------------------------
def test_request_approval_rejection(harness_factory):
    def reject(cp: Checkpoint) -> ApprovalRecord:
        return ApprovalRecord(checkpoint=cp.name, state=ApprovalState.REJECTED,
                              approver="human")

    h = harness_factory(approval_fn=reject)
    rec = h.request_approval(Checkpoint(name="pre_merge", summary="merge?"))
    assert rec.state == ApprovalState.REJECTED


# 8. Usage is populated and non-negative ------------------------------------
def test_usage_non_negative(harness_factory):
    res = harness_factory().dispatch_subagent(_task()).wait(timeout_s=5)
    u = res.usage
    assert u.input_tokens >= 0 and u.output_tokens >= 0 and u.usd >= 0.0

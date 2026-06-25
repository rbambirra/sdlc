"""
Smoke test — drive the full pipeline end-to-end with the mock harness/board/vcs.
Proves the flow walks DoR -> ... -> PR -> DEV-DONE, hits gates and checkpoints.
"""
from __future__ import annotations

from core.pipeline import Pipeline
from core.risk import RiskClassifier, RiskLevel
from core.state import StateStore
from adapters.harness.mock.mock_harness import MockBoard, MockHarness, MockVcs


def _pipeline(tmp_path, **hkw):
    return Pipeline(
        harness=MockHarness(**hkw),
        board=MockBoard(),
        vcs=MockVcs(),
        classifier=RiskClassifier(threshold=RiskLevel.MEDIUM),
        store=StateStore(root=str(tmp_path)),
    )


def test_happy_path_reaches_dev_done(tmp_path):
    res = _pipeline(tmp_path).run("DEMO-1")
    assert res.ok, f"blocked: {res.block_reason}\n" + "\n".join(res.log)
    assert res.final_phase == "done"
    assert res.pr_ref.startswith("PR-")
    # the flow actually walked the phases
    joined = "\n".join(res.log)
    assert "[DoR] passed" in joined
    assert "[judge:plan] GO" in joined
    assert "[PR] opened" in joined
    assert "[DEV-DONE] complete" in joined


def test_dor_blocks_unready_item(tmp_path):
    board = MockBoard()
    # an item with no acceptance criteria fails DoR
    board._items["BAD-1"] = {"id": "BAD-1", "title": "x", "acceptance_criteria": []}
    p = Pipeline(MockHarness(), board, MockVcs(), store=StateStore(root=str(tmp_path)))
    res = p.run("BAD-1")
    assert not res.ok
    assert res.blocked
    assert "Definition of Ready" in res.block_reason


def test_plan_judge_nogo_blocks(tmp_path):
    from core.capabilities import GateResult, Finding

    def gate_fn(name, inputs):
        if name == "judge_plan":
            return GateResult(passed=False, findings=[Finding("block", "bad plan")])
        return GateResult(passed=True)

    res = _pipeline(tmp_path, gate_fn=gate_fn).run("DEMO-1")
    assert not res.ok
    assert "plan judge NO-GO" in res.block_reason


def test_dod_gate_failure_blocks(tmp_path):
    from core.capabilities import GateResult, Finding

    def gate_fn(name, inputs):
        if name == "held_out_tests":
            return GateResult(passed=False, findings=[Finding("block", "held-out failed")])
        return GateResult(passed=True)

    res = _pipeline(tmp_path, gate_fn=gate_fn).run("DEMO-1")
    assert not res.ok
    assert "DoD gate failed" in res.block_reason


def test_hard_sensitive_requires_approval_and_can_reject(tmp_path):
    from core.capabilities import ApprovalRecord, ApprovalState, Checkpoint

    board = MockBoard()
    # make the item hard-sensitive (auth)
    board._items["AUTH-1"] = {
        "id": "AUTH-1", "title": "change auth token validation",
        "description": "rework oauth session login",
        "acceptance_criteria": ["Given a token, when invalid, then 401."],
        "state": "Ready",
    }

    def reject(cp: Checkpoint) -> ApprovalRecord:
        return ApprovalRecord(checkpoint=cp.name, state=ApprovalState.REJECTED, approver="human")

    p = Pipeline(MockHarness(approval_fn=reject), board, MockVcs(),
                 store=StateStore(root=str(tmp_path)))
    res = p.run("AUTH-1")
    assert not res.ok
    assert "approval: rejected" in res.block_reason
    # proves hard-sensitive forced the human gate
    assert any("checkpoint:spec" in line and "rejected" in line for line in res.log)


def test_state_is_resumable(tmp_path):
    store = StateStore(root=str(tmp_path))
    p = Pipeline(MockHarness(), MockBoard(), MockVcs(), store=store)
    res = p.run("DEMO-1", job_id="resume-job")
    assert res.ok
    # state persisted and reloadable
    st = store.load("resume-job")
    assert st is not None
    assert st.phase == "done"
    assert "spec" in st.artifacts

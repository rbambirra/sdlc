"""
pipeline.py — the orchestrator.

Chains the SDLC phases (DoR -> ... -> PR) by calling ABSTRACT capabilities.
It never imports a harness SDK. Claude / Codex / Hermes are injected as a
`Harness`; the board and VCS as `Board` / `Vcs`. This is what makes the whole
thing portable: the flow is here, the translation is in the adapters.

Honors:
- DoR as a hard entry block.
- Continuous risk re-classification (spec, plan, decompose, pre-merge).
- Human checkpoints conditional on risk (hard-sensitive => non-overridable).
- Orthogonal DoD gate (the implementer is never its own oracle).
- Resumable state (checkpoint after every phase).
"""
from __future__ import annotations

from dataclasses import dataclass

from core.capabilities import (
    ApprovalState,
    Board,
    Checkpoint,
    GateResult,
    Harness,
    JobStatus,
    Task,
    Vcs,
)
from core.risk import RiskAssessment, RiskClassifier, RiskLevel
from core.state import Phase, PipelineState, StateStore


@dataclass
class PipelineResult:
    job_id: str
    ok: bool
    final_phase: str
    pr_ref: str = ""
    blocked: bool = False
    block_reason: str = ""
    log: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.log is None:
            self.log = []


# The orthogonal DoD gates (introduced incrementally; held-out runs in the gate)
DOD_GATES = [
    "held_out_tests", "mutation", "typecheck_lint", "contract",
    "deps_scan", "secret_scan", "sast", "e2e",
]

# Dev loop: implement -> review -> gate -> judge, retry on NO-GO up to this many
# rounds, feeding the findings back to the implementer each round. If the judge
# still fails after the last round, escalate to a human instead of dead-ending.
MAX_REVIEW_ROUNDS = 5


class Pipeline:
    def __init__(self, harness: Harness, board: Board, vcs: Vcs,
                 classifier: RiskClassifier | None = None,
                 store: StateStore | None = None,
                 interactive_approvals: bool = True):
        self.h = harness
        self.board = board
        self.vcs = vcs
        self.classifier = classifier or RiskClassifier()
        self.store = store or StateStore()
        # interactive=True (dev mode) vs durable approval service (service mode)
        self.interactive_approvals = interactive_approvals

    # -- helpers -----------------------------------------------------------
    def _log(self, res: PipelineResult, msg: str) -> None:
        res.log.append(msg)

    def _checkpoint(self, res: PipelineResult, name: str, summary: str,
                    risk: RiskAssessment) -> bool:
        """Request a human checkpoint IF risk requires it. Returns True to
        proceed, False to stop. Hard-sensitive is non-overridable."""
        if not risk.requires_human:
            self._log(res, f"[checkpoint:{name}] skipped (low risk -> full-agent)")
            return True
        policy = "codeowner:" + ",".join(risk.classes) if risk.classes else ""
        rec = self.h.request_approval(Checkpoint(name=name, summary=summary,
                                                 required_policy=policy))
        self._log(res, f"[checkpoint:{name}] {rec.state.value} by {rec.approver or '?'}")
        if rec.state == ApprovalState.APPROVED:
            return True
        if rec.state == ApprovalState.EDITED:
            self._log(res, f"[checkpoint:{name}] artifact edited -> re-validate")
            return True  # caller re-validates downstream
        # rejected / timed_out -> stop
        res.blocked = True
        res.block_reason = f"{name} approval: {rec.state.value}"
        return False

    def _dispatch(self, res: PipelineResult, role: str, instructions: str,
                  context: dict) -> str:
        handle = self.h.dispatch_subagent(
            Task(role=role, instructions=instructions, context=context))
        r = handle.wait(timeout_s=600)
        self._log(res, f"[{role}] {r.status.value} (tok in={r.usage.input_tokens} out={r.usage.output_tokens})")
        if r.status != JobStatus.DONE:
            res.blocked = True
            res.block_reason = f"{role} {r.status.value}: {r.error}"
        return r.output

    # -- the flow ----------------------------------------------------------
    def run(self, work_item_id: str, job_id: str | None = None) -> PipelineResult:
        job_id = job_id or f"job-{work_item_id}"
        state: PipelineState = self.store.load_or_create(job_id, work_item_id)
        res = PipelineResult(job_id=job_id, ok=False, final_phase=state.phase)

        item = self.board.get_work_item(work_item_id)

        # --- DoR: hard entry block ---
        if not self._definition_of_ready(item):
            res.blocked = True
            res.block_reason = "Definition of Ready failed"
            res.final_phase = Phase.DOR.value
            self._log(res, "[DoR] BLOCKED — not ready for development")
            return res
        self._log(res, "[DoR] passed")
        state.advance(Phase.RISK); self.store.save(state)

        # --- risk (1st classification) ---
        text = item.get("title", "") + " " + item.get("description", "")
        risk = self.classifier.classify(text=text)
        self._log(res, f"[risk] {risk.level.value} classes={risk.classes}")
        state.advance(Phase.SPEC); self.store.save(state)

        # --- spec + AC testable (QA shift-left) ---
        self.board.transition(work_item_id, "Active")
        spec = self._dispatch(res, "spec", "Write a spec reconciling the work item with repo constraints; QA derives testable AC.", {"item": item})
        if res.blocked:
            return self._finish(res, state)
        state.artifacts["spec"] = spec
        # re-risk on spec
        risk = self.classifier.classify(text=text + " " + spec)
        if not self._checkpoint(res, "spec", "Approve the spec + acceptance criteria", risk):
            return self._finish(res, state)
        state.advance(Phase.SCOPE); self.store.save(state)

        # --- scope (FE/BE/mixed) ---
        scope = self._dispatch(res, "scope", "Detect scope: FE / BE / FE+BE / mixed. Ambiguous -> mixed.", {"item": item, "spec": spec})
        state.artifacts["scope"] = scope
        state.advance(Phase.PLAN); self.store.save(state)

        # --- plan + judge of a different model ---
        plan = self._dispatch(res, "plan", "Write a versioned plan: paths, complete code, TDD order, conventional commits.", {"spec": spec, "scope": scope})
        if res.blocked:
            return self._finish(res, state)
        state.artifacts["plan"] = plan
        judge = self.h.run_gate("judge_plan", {"plan": plan})
        self._log(res, f"[judge:plan] {'GO' if judge.passed else 'NO-GO'} ({len(judge.findings)} findings)")
        if not judge.passed:
            res.blocked = True
            res.block_reason = "plan judge NO-GO"
            return self._finish(res, state)
        # re-risk on plan
        risk = self.classifier.classify(text=text + " " + plan)
        if not self._checkpoint(res, "plan", "Approve the plan before coding", risk):
            return self._finish(res, state)
        state.advance(Phase.DECOMPOSE); self.store.save(state)

        # --- decompose + dev loop (per task), bounded retry with feedback ---
        # MVP: single task; production splits into branch+worktree per task.
        # Loop: implement -> review -> DoD gate -> holistic judge. On NO-GO,
        # feed the findings back and retry, up to MAX_REVIEW_ROUNDS. If the
        # judge still fails after the last round, escalate to a human (B).
        impl = ""
        feedback: list[str] = []
        passed = False
        for rnd in range(1, MAX_REVIEW_ROUNDS + 1):
            self._log(res, f"[dev-loop] round {rnd}/{MAX_REVIEW_ROUNDS}")
            ctx = {"plan": plan}
            if feedback:
                # Prior round's findings become explicit fix instructions.
                ctx["previous_findings"] = "\n".join(feedback)
            impl = self._dispatch(
                res, "implementer",
                "Implement the plan (TDD). You do NOT own the held-out oracle."
                + (" Address the previous_findings before anything else." if feedback else ""),
                ctx)
            if res.blocked:
                return self._finish(res, state)

            self._dispatch(res, "spec_reviewer", "Review code vs spec compliance.", {"spec": spec, "impl": impl})
            self._dispatch(res, "quality_reviewer", "Review code quality.", {"impl": impl})
            self._dispatch(res, "qa", "Verify coverage vs AC (each AC has a test that proves it).", {"item": item, "impl": impl})

            # --- orthogonal DoD gate (held-out runs in the gate, not the implementer) ---
            gate_ok, gate_findings = self._dod_gate(res)
            # --- holistic review (independent judge) ---
            holistic = self.h.run_gate("judge_code", {"impl": impl})
            self._log(res, f"[judge:code] {'GO' if holistic.passed else 'NO-GO'}")

            if gate_ok and holistic.passed:
                passed = True
                break

            # collect findings for the next round's implementer
            feedback = []
            if not gate_ok:
                feedback += [str(f) for f in gate_findings]
            if not holistic.passed:
                feedback += [f.message for f in holistic.findings] or ["holistic judge NO-GO"]
            self._log(res, f"[dev-loop] round {rnd} NO-GO ({len(feedback)} findings) -> retry" if rnd < MAX_REVIEW_ROUNDS else f"[dev-loop] round {rnd} NO-GO (final round)")

        state.advance(Phase.REVIEW); self.store.save(state)

        if not passed:
            # B: judge still failing after MAX_REVIEW_ROUNDS -> involve a human
            # rather than dead-ending. Hard-sensitive policy not required here;
            # this is an escalation gate, the approver decides go/no-go.
            self._log(res, f"[dev-loop] exhausted {MAX_REVIEW_ROUNDS} rounds, still NO-GO -> escalate to human")
            rec = self.h.request_approval(Checkpoint(
                name="review_escalation",
                summary=f"Dev loop failed the judge after {MAX_REVIEW_ROUNDS} rounds. "
                        f"Last findings:\n" + "\n".join(feedback[:10]),
                required_policy="codeowner"))
            self._log(res, f"[checkpoint:review_escalation] {rec.state.value} by {rec.approver or '?'}")
            if rec.state not in (ApprovalState.APPROVED, ApprovalState.EDITED):
                res.blocked = True
                res.block_reason = f"review escalation: {rec.state.value} after {MAX_REVIEW_ROUNDS} rounds"
                return self._finish(res, state)

        state.advance(Phase.PR); self.store.save(state)

        # --- pre-merge re-risk + checkpoint ---
        risk = self.classifier.classify(text=text + " " + impl)
        # --- PR ---
        branch = f"feat/{work_item_id}"
        self.vcs.push_branch(branch)
        pr_ref = self.vcs.open_pr(branch, "main", f"[#{work_item_id}] {item.get('title','')}", state.artifacts.get("spec", "")[:200])
        res.pr_ref = pr_ref
        self.board.transition(work_item_id, "Review")
        self._log(res, f"[PR] opened {pr_ref}")
        if not self._checkpoint(res, "pre_merge", f"Approve merge of {pr_ref}", risk):
            return self._finish(res, state)

        state.advance(Phase.DONE); self.store.save(state)
        res.ok = True
        res.final_phase = Phase.DONE.value
        self._log(res, "[DEV-DONE] complete")
        return res

    # -- phase helpers -----------------------------------------------------
    def _definition_of_ready(self, item: dict) -> bool:
        """Hard gate. Criteria come from project setup; MVP checks the basics."""
        if not item.get("title"):
            return False
        if not item.get("acceptance_criteria"):
            return False
        return True

    def _dod_gate(self, res: PipelineResult) -> tuple[bool, list]:
        findings = []
        for gate in DOD_GATES:
            gr: GateResult = self.h.run_gate(gate, {})
            self._log(res, f"[dod:{gate}] {'pass' if gr.passed else 'FAIL'}")
            if not gr.passed:
                findings.extend(gr.findings or [gate])
        return (len(findings) == 0, findings)

    def _finish(self, res: PipelineResult, state: PipelineState) -> PipelineResult:
        state.blocked = res.blocked
        state.block_reason = res.block_reason
        self.store.save(state)
        res.final_phase = state.phase
        return res

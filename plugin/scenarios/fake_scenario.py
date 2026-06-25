#!/usr/bin/env python3
"""
fake_scenario.py — drive the FULL pipeline end-to-end with a REAL harness.

This is the no-mock proof. The mock smoke test proves the flow walks the phases;
this proves the CORE can drive a REAL coding-agent harness (Codex / Claude)
through every phase against a fake-but-realistic work item.

Three ports, three levels of reality:
  - Harness  -> REAL. codex exec / claude -p hit an actual model. Each phase
                (spec, scope, plan, implementer, reviewers, qa) is a real call.
  - Board    -> FAKE in-memory (FakeBoard). We have no Jira/ADO in the sandbox;
                it serves one pre-loaded work item and logs transitions.
  - Vcs      -> FAKE in-memory (FakeVcs). We do NOT open a real PR from a test;
                it records push/open_pr so we can assert the flow reached PR.

Gates (DoD) and approvals use the CliHarnessBase defaults: gates auto-pass and
approvals auto-approve. That keeps the headless run from blocking on a human.
The work item is intentionally LOW risk so no human checkpoint activates and the
pipeline runs full-agent. (Flip USE_SENSITIVE_ITEM=True to see a HARD_SENSITIVE
checkpoint fire and auto-approve.)

This is NOT a pytest test: it invokes real models (slow, costs tokens, needs the
CLI + Flow proxy). Run it on demand:

    cd plugin && python3 scenarios/fake_scenario.py            # both harnesses
    cd plugin && python3 scenarios/fake_scenario.py codex      # just codex
    cd plugin && python3 scenarios/fake_scenario.py claude     # just claude
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path
from typing import Any

# allow `python3 scenarios/fake_scenario.py` from the plugin dir
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.capabilities import Board, Vcs
from core.pipeline import Pipeline
from core.risk import RiskClassifier, RiskLevel
from core.state import StateStore
from adapters.harness.claude.claude_harness import ClaudeHarness
from adapters.harness.codex.codex_harness import CodexHarness

USE_SENSITIVE_ITEM = False  # True -> work item trips HARD_SENSITIVE -> checkpoint


# --------------------------------------------------------------------------
# Fake (not mock) Board / Vcs: real in-memory behavior, no network.
# "Fake" = a working lightweight implementation; "mock" = canned/asserted stub.
# --------------------------------------------------------------------------
class FakeBoard(Board):
    name = "fake"

    def __init__(self) -> None:
        self.log: list[str] = []
        title = ("Add a CSV export button to the reports page"
                 if not USE_SENSITIVE_ITEM else
                 "Rotate the OAuth signing key and migrate the sessions table")
        ac = (["Given the reports page, when I click Export, then a CSV downloads.",
               "Given an empty report, then the button is disabled with a tooltip."]
              if not USE_SENSITIVE_ITEM else
              ["Given a key rotation, then all live sessions stay valid.",
               "Given the migration, then no session row is lost."])
        self._item = {
            "id": "PROJ-42",
            "title": title,
            "type": "User Story",
            "description": "As a user I want " + title.lower() + ".",
            "acceptance_criteria": ac,
            "state": "Ready",
        }

    def get_work_item(self, item_id: str) -> dict[str, Any]:
        return dict(self._item, id=item_id)

    def transition(self, item_id: str, state: str) -> None:
        self.log.append(f"transition {item_id} -> {state}")

    def comment(self, item_id: str, body: str) -> None:
        self.log.append(f"comment {item_id}: {body[:50]}")

    def create_ticket(self, title: str, body: str, kind: str) -> str:
        tid = f"PROJ-{int(time.time()) % 1000}"
        self.log.append(f"create_ticket {tid} [{kind}] {title[:30]}")
        return tid


class FakeVcs(Vcs):
    name = "fake"

    def __init__(self) -> None:
        self.log: list[str] = []

    def push_branch(self, branch: str) -> None:
        self.log.append(f"push {branch}")

    def open_pr(self, branch: str, base: str, title: str, body: str) -> str:
        ref = "PR-fake-1"
        self.log.append(f"open_pr {ref} {branch}->{base} :: {title[:40]}")
        return ref

    def get_checks_status(self, pr_ref: str) -> dict[str, str]:
        return {"required": "success"}


# --------------------------------------------------------------------------
def _show_worktrees(harness, label: str) -> None:
    """If the harness materialized code in builder worktrees, show what it
    produced so the two harnesses can be compared on REAL output."""
    import os
    wts = getattr(harness, "_worktrees", {})
    if not wts:
        return
    print(f"\n--- {label}: code produced (builder worktrees) ---")
    for wt in wts.values():
        if not (wt and os.path.isdir(wt)):
            continue
        files = [f for f in sorted(os.listdir(wt))
                 if not f.startswith(".") and f != "__pycache__"]
        print(f"  worktree: {wt}")
        for f in files:
            p = os.path.join(wt, f)
            try:
                n = sum(1 for _ in open(p, encoding="utf-8", errors="replace"))
                print(f"    - {f} ({n} lines)")
            except OSError:
                print(f"    - {f}")


def run_with(harness, label: str) -> bool:
    print(f"\n{'='*70}\n  FAKE SCENARIO — real harness: {label}\n{'='*70}")
    board = FakeBoard()
    vcs = FakeVcs()
    # MEDIUM threshold: LOW item runs full-agent (no human); sensitive item trips
    # HARD_SENSITIVE and the auto-approver (CliHarnessBase default) approves it.
    pipe = Pipeline(
        harness=harness,
        board=board,
        vcs=vcs,
        classifier=RiskClassifier(threshold=RiskLevel.MEDIUM),
        store=StateStore(root=f"/tmp/sdlc-fake-{label}"),
    )
    t0 = time.monotonic()
    res = pipe.run("PROJ-42")
    dt = time.monotonic() - t0

    print("\n--- pipeline log ---")
    for line in res.log:
        print("  " + line)
    _show_worktrees(harness, label)
    print("\n--- board log ---")
    for line in board.log:
        print("  " + line)
    print("--- vcs log ---")
    for line in vcs.log:
        print("  " + line)

    print(f"\n--- result ({dt:.1f}s) ---")
    print(f"  ok={res.ok}  final_phase={res.final_phase}  pr_ref={res.pr_ref!r}")
    if res.blocked:
        print(f"  BLOCKED: {res.block_reason}")
    verdict = "PASS" if res.ok and res.pr_ref else "FAIL"
    print(f"  ==> {label}: {verdict}")
    return res.ok and bool(res.pr_ref)


def main() -> int:
    which = sys.argv[1].lower() if len(sys.argv) > 1 else "both"
    targets = []
    if which in ("both", "codex"):
        targets.append(("codex", CodexHarness, "codex"))
    if which in ("both", "claude"):
        targets.append(("claude", ClaudeHarness, "claude"))

    results: dict[str, bool] = {}
    for label, cls, binary in targets:
        if shutil.which(binary) is None:
            print(f"\n[skip] {label}: '{binary}' not on PATH")
            results[label] = None  # type: ignore[assignment]
            continue
        try:
            results[label] = run_with(cls(), label)
        except Exception as exc:  # noqa: BLE001 - scenario must report, not crash
            print(f"\n[error] {label} raised: {exc}")
            results[label] = False

    print(f"\n{'='*70}\n  SUMMARY\n{'='*70}")
    for label, ok in results.items():
        tag = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
        print(f"  {label:8s} {tag}")
    real = [v for v in results.values() if v is not None]
    return 0 if real and all(real) else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""
risk.py — risk classification + autonomy modulation.

Base risk matrix ships in the template; projects calibrate the threshold at
setup. Risk is RE-CLASSIFIED at multiple points (spec, plan, diff, pre-merge) —
not once. Hard-sensitive classes force a non-overridable human gate regardless
of the project threshold.

The classifier here is the ORCHESTRATOR-side view (intent/scope). The real
non-bypassable enforcement is the server-side semantic re-risking check
(see ../enforcement/), independent of what the agent declares.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HARD_SENSITIVE = "hard_sensitive"  # always needs a human gate


# Base matrix: capability -> patterns that signal it. Projects extend this.
DEFAULT_SENSITIVE_PATTERNS: dict[str, list[str]] = {
    "auth": [r"\bauth", r"\btoken\b", r"\bsession\b", r"\bpassword\b", r"\boauth\b", r"login"],
    "payment": [r"\bpayment\b", r"\bcharge\b", r"\bbilling\b", r"\binvoice\b", r"stripe|paypal"],
    "migration": [r"\bmigration\b", r"\balter table\b", r"\bdrop table\b", r"\bDDL\b", r"schema change"],
    "secrets": [r"\bsecret\b", r"\bcredential\b", r"\bapi[_-]?key\b", r"\bprivate[_-]?key\b"],
    "infra": [r"\bterraform\b", r"\bkubernetes\b", r"\bhelm\b", r"\biam\b", r"\bdeploy\b"],
    "multi_repo": [],  # set by scope detection, not text
}

HARD_SENSITIVE_CLASSES = {"auth", "payment", "migration", "secrets", "infra"}


@dataclass
class RiskAssessment:
    level: RiskLevel
    classes: list[str] = field(default_factory=list)   # which sensitive classes triggered
    reasons: list[str] = field(default_factory=list)
    requires_human: bool = False

    @property
    def is_hard_sensitive(self) -> bool:
        return self.level == RiskLevel.HARD_SENSITIVE


class RiskClassifier:
    def __init__(self, patterns: dict[str, list[str]] | None = None,
                 threshold: RiskLevel = RiskLevel.MEDIUM):
        self.patterns = patterns or DEFAULT_SENSITIVE_PATTERNS
        # Above this level (inclusive) a human checkpoint activates.
        self.threshold = threshold

    def classify(self, *, text: str = "", changed_paths: list[str] | None = None,
                 multi_repo: bool = False) -> RiskAssessment:
        """Combine textual/semantic signal + path signal + multi-repo flag.
        Re-call this at spec/plan/diff/pre-merge — it is the same function."""
        changed_paths = changed_paths or []
        haystack = (text + " " + " ".join(changed_paths)).lower()
        hit_classes: list[str] = []
        reasons: list[str] = []

        for cls, pats in self.patterns.items():
            for pat in pats:
                if pat and re.search(pat, haystack, re.IGNORECASE):
                    hit_classes.append(cls)
                    reasons.append(f"matched {cls!r} via /{pat}/")
                    break

        if multi_repo:
            hit_classes.append("multi_repo")
            reasons.append("multi-repo change")

        hard = sorted(set(hit_classes) & HARD_SENSITIVE_CLASSES)
        if hard:
            return RiskAssessment(level=RiskLevel.HARD_SENSITIVE, classes=sorted(set(hit_classes)),
                                  reasons=reasons, requires_human=True)
        if hit_classes:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        requires_human = self._meets_threshold(level)
        return RiskAssessment(level=level, classes=sorted(set(hit_classes)),
                              reasons=reasons, requires_human=requires_human)

    def _meets_threshold(self, level: RiskLevel) -> bool:
        order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2,
                 RiskLevel.HARD_SENSITIVE: 3}
        return order[level] >= order[self.threshold]

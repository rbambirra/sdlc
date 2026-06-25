#!/usr/bin/env python3
"""
rerisk_check.py — semantic re-risking check (server-side, agent-independent).

THE control that makes risk non-bypassable. It does NOT trust the agent's label
or PR description. It inspects the DIFF for sensitive CAPABILITY introduced
anywhere — not just sensitive path names — so an agent relocating sensitive
behavior to an "innocent" path is still caught.

Fail-closed: generated/minified/binary/vendored or un-inspectable changes
require human review instead of passing by omission.

Exit 0 = no hard-sensitive capability (or human owner already required).
Exit 2 = hard-sensitive capability detected -> requires human owner review.
Exit 3 = fail-closed (un-inspectable) -> requires human review.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

# Semantic signals: capability -> regexes matched against ADDED diff lines.
CAPABILITY_PATTERNS: dict[str, list[str]] = {
    "auth": [r"jwt", r"oauth", r"session", r"set[-_ ]?cookie", r"authenticat", r"authoriz",
             r"verify_token", r"bearer"],
    "crypto": [r"\bAES\b", r"\bRSA\b", r"hashlib", r"crypto", r"\bsign\b", r"\bhmac\b", r"private_key"],
    "migration": [r"ALTER TABLE", r"DROP TABLE", r"CREATE TABLE", r"\bmigration\b", r"add_column",
                  r"drop_column"],
    "payment": [r"stripe", r"paypal", r"\bcharge\b", r"\bpayment\b", r"\bbilling\b", r"card_number"],
    "secret_io": [r"os\.environ\[", r"getenv\(", r"\bsecret\b", r"api[_-]?key", r"vault"],
    "infra": [r"terraform", r"kubernetes", r"\bhelm\b", r"\biam\b", r"boto3", r"subprocess"],
}

FAIL_CLOSED_HINTS = [r"\.min\.js$", r"vendor/", r"node_modules/", r"\.lock$", r"generated", r"\beval\(", r"reflect"]


def added_lines(base: str) -> tuple[list[str], list[str]]:
    out = subprocess.run(["git", "diff", f"{base}...HEAD", "--unified=0"],
                         capture_output=True, text=True, check=True).stdout
    added, files = [], []
    for ln in out.splitlines():
        if ln.startswith("+++ b/"):
            files.append(ln[6:])
        elif ln.startswith("+") and not ln.startswith("+++"):
            added.append(ln[1:])
    return added, files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args()

    added, files = added_lines(args.base)
    blob = "\n".join(added)

    # fail-closed on un-inspectable content
    for f in files:
        if any(re.search(h, f) for h in FAIL_CLOSED_HINTS):
            print(f"FAIL-CLOSED: un-inspectable change in {f} -> requires human review")
            return 3
    for h in FAIL_CLOSED_HINTS:
        if re.search(h, blob):
            print(f"FAIL-CLOSED: pattern /{h}/ in diff -> requires human review")
            return 3

    hits = []
    for cap, pats in CAPABILITY_PATTERNS.items():
        for p in pats:
            if re.search(p, blob, re.IGNORECASE):
                hits.append((cap, p))
                break
    if hits:
        print("HARD-SENSITIVE capability detected (requires human owner review):")
        for cap, p in hits:
            print(f"  - {cap} (via /{p}/)")
        return 2
    print("No hard-sensitive capability detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
GitHub VCS adapter (reference).

Implements the Vcs contract: RUNTIME operations only — push a feature branch,
open a PR, read checks status. It does NOT touch branch protection, required
checks, CODEOWNERS, or identity — those are the separate admin/ bootstrap path,
unavailable to the agent (enforcement Principle 0/1).

Auth: GITHUB_TOKEN env (least-privilege: repo contents + PR, no admin).
Push uses git; PR/checks use the REST API via stdlib urllib (no deps).
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from typing import Any


class GitHubVcs:
    name = "github"

    def __init__(self, repo: str | None = None, token: str | None = None,
                 workdir: str | None = None):
        # repo as "owner/name"
        self.repo = repo or os.environ.get("GITHUB_REPO", "")
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.workdir = workdir or os.getcwd()

    def _api(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        url = f"https://api.github.com{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        if data:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}

    def push_branch(self, branch: str) -> None:
        subprocess.run(["git", "push", "-u", "origin", branch],
                       cwd=self.workdir, check=True, capture_output=True, text=True)

    def open_pr(self, branch: str, base: str, title: str, body: str) -> str:
        d = self._api("POST", f"/repos/{self.repo}/pulls",
                      {"title": title, "head": branch, "base": base, "body": body})
        return d.get("html_url", str(d.get("number", "")))

    def get_checks_status(self, pr_ref: str) -> dict[str, str]:
        # pr_ref may be a number; resolve head sha then read check-runs
        num = pr_ref.rstrip("/").split("/")[-1]
        pr = self._api("GET", f"/repos/{self.repo}/pulls/{num}")
        sha = (pr.get("head") or {}).get("sha", "")
        if not sha:
            return {}
        runs = self._api("GET", f"/repos/{self.repo}/commits/{sha}/check-runs")
        return {r["name"]: r.get("conclusion") or r.get("status", "")
                for r in runs.get("check_runs", [])}

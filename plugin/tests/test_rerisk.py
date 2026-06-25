"""
Test the semantic re-risking check — the anti-bypass control.

Proves it detects sensitive CAPABILITY by content (not path name), so an agent
hiding auth/crypto/migration code in an 'innocent' path is still caught, and
that it fails closed on un-inspectable content.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RERISK = Path(__file__).resolve().parents[1] / "enforcement" / "rerisk_check.py"


def _git(cmd, cwd):
    subprocess.run(["git", *cmd], cwd=cwd, check=True, capture_output=True, text=True)


def _repo(tmp_path):
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@t"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    (tmp_path / "readme.md").write_text("# x\n")
    _git(["add", "-A"], tmp_path)
    _git(["commit", "-qm", "base"], tmp_path)
    _git(["branch", "-M", "main"], tmp_path)
    _git(["checkout", "-qb", "feat"], tmp_path)
    return tmp_path


def _run(cwd):
    return subprocess.run([sys.executable, str(RERISK), "--base", "main"],
                          cwd=cwd, capture_output=True, text=True)


def test_detects_sensitive_capability_in_innocent_path(tmp_path):
    r = _repo(tmp_path)
    # auth capability hidden in a file named 'utils/helpers.py'
    (r / "utils").mkdir()
    (r / "utils" / "helpers.py").write_text(
        "def f(req):\n    token = req.headers['authorization']\n    return verify_token(token)\n")
    _git(["add", "-A"], r)
    _git(["commit", "-qm", "feat: helper"], r)
    res = _run(r)
    assert res.returncode == 2, res.stdout + res.stderr
    assert "auth" in res.stdout


def test_clean_change_passes(tmp_path):
    r = _repo(tmp_path)
    (r / "copy.py").write_text("def add(a, b):\n    return a + b\n")
    _git(["add", "-A"], r)
    _git(["commit", "-qm", "feat: add"], r)
    res = _run(r)
    assert res.returncode == 0, res.stdout


def test_fail_closed_on_uninspectable(tmp_path):
    r = _repo(tmp_path)
    (r / "bundle.min.js").write_text("var a=1;" * 50)
    _git(["add", "-A"], r)
    _git(["commit", "-qm", "chore: bundle"], r)
    res = _run(r)
    assert res.returncode == 3, res.stdout

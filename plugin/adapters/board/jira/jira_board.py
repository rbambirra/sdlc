"""
Jira board adapter (reference).

Implements the Board contract over the Jira Cloud REST API v3. Auth via
JIRA_BASE_URL + JIRA_EMAIL + JIRA_API_TOKEN env vars (basic auth). Network calls
use stdlib urllib so the adapter has no third-party deps.

Board transitions are NON-BLOCKING by contract: if a call fails, the caller logs
and continues (the deliverable is the PR, not the board state).
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any


class JiraBoard:
    name = "jira"

    def __init__(self, base_url: str | None = None, email: str | None = None,
                 token: str | None = None):
        self.base_url = (base_url or os.environ.get("JIRA_BASE_URL", "")).rstrip("/")
        email = email or os.environ.get("JIRA_EMAIL", "")
        token = token or os.environ.get("JIRA_API_TOKEN", "")
        self._auth = base64.b64encode(f"{email}:{token}".encode()).decode()

    def _req(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Basic {self._auth}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}

    def get_work_item(self, item_id: str) -> dict[str, Any]:
        d = self._req("GET", f"/rest/api/3/issue/{item_id}")
        fields = d.get("fields", {})
        return {
            "id": d.get("key", item_id),
            "title": fields.get("summary", ""),
            "type": (fields.get("issuetype") or {}).get("name", ""),
            "description": _adf_to_text(fields.get("description")),
            "acceptance_criteria": _split_ac(fields),
            "state": (fields.get("status") or {}).get("name", ""),
        }

    def transition(self, item_id: str, state: str) -> None:
        # find the transition id whose target status name matches `state`
        tr = self._req("GET", f"/rest/api/3/issue/{item_id}/transitions")
        match = next((t for t in tr.get("transitions", [])
                      if (t.get("to") or {}).get("name", "").lower() == state.lower()), None)
        if not match:
            raise ValueError(f"no transition to '{state}' for {item_id}")
        self._req("POST", f"/rest/api/3/issue/{item_id}/transitions",
                  {"transition": {"id": match["id"]}})

    def comment(self, item_id: str, body: str) -> None:
        self._req("POST", f"/rest/api/3/issue/{item_id}/comment",
                  {"body": _text_to_adf(body)})

    def create_ticket(self, title: str, body: str, kind: str) -> str:
        project = os.environ.get("JIRA_PROJECT_KEY", "")
        d = self._req("POST", "/rest/api/3/issue", {
            "fields": {
                "project": {"key": project},
                "summary": title,
                "description": _text_to_adf(body),
                "issuetype": {"name": kind or "Task"},
            }
        })
        return d.get("key", "")


# --- minimal ADF (Atlassian Document Format) helpers ---------------------
def _text_to_adf(text: str) -> dict:
    return {"type": "doc", "version": 1,
            "content": [{"type": "paragraph",
                         "content": [{"type": "text", "text": text or ""}]}]}


def _adf_to_text(adf: Any) -> str:
    if not isinstance(adf, dict):
        return str(adf or "")
    out: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "text":
                out.append(node.get("text", ""))
            for c in node.get("content", []) or []:
                walk(c)
    walk(adf)
    return " ".join(out).strip()


def _split_ac(fields: dict) -> list[str]:
    # AC often lives in a custom field or the description; project configures it.
    raw = fields.get("customfield_acceptance") or ""
    if isinstance(raw, dict):
        raw = _adf_to_text(raw)
    return [ln.strip("-* ").strip() for ln in str(raw).splitlines() if ln.strip()]

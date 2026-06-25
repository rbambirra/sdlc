#!/usr/bin/env bash
# admin/bootstrap.sh — SEPARATE admin path. Runs with HUMAN ADMIN credentials,
# NEVER available to the orchestrator/worker (enforcement Principle 0/1).
#
# Materializes enforcement (branch protection, required checks, CODEOWNERS, PR
# template) and creates the scoped agent identity. The agent can NEVER run this
# — it has no admin token and the worker network/IAM cannot reach it.
#
# Usage (human admin, once per repo):  bash admin/bootstrap.sh <owner/repo>
set -euo pipefail

REPO="${1:?usage: bootstrap.sh <owner/repo>}"
: "${ADMIN_GITHUB_TOKEN:?set ADMIN_GITHUB_TOKEN (human admin PAT; NOT the agent token)}"

TOKEN_VAR="ADMIN_GITHUB_TOKEN"
api() { curl -fsSL -X "$1" -H "Authorization: Bearer ${!TOKEN_VAR}" \
  -H "Accept: application/vnd.github+json" "https://api.github.com$2" ${3:+-d "$3"}; }

echo "==> Materializing enforcement on ${REPO} (admin path)"

echo "  - copying enforcement templates into the repo working tree"
echo "    (PR template, CODEOWNERS, required-checks workflow, pre-commit)"
echo "    do this in a human-reviewed PR; do not let the agent author it."

echo "  - enabling branch protection + required checks on main"
api PUT "/repos/${REPO}/branches/main/protection" '{
  "required_status_checks": {"strict": true, "contexts": ["sdlc-required-checks"]},
  "enforce_admins": true,
  "required_pull_request_reviews": {"required_approving_review_count": 1,
    "require_code_owner_reviews": true},
  "restrictions": null
}' >/dev/null && echo "    branch protection set"

echo "==> Creating the scoped AGENT identity"
echo "  - the agent token must be LEAST-PRIVILEGE: contents:write + pull_requests:write"
echo "  - it must NOT have: admin, branch-protection write, PR approve, secrets write"
echo "  - issue/store it via your IdP/secret manager; inject into the worker per job"
echo "  - the worker network/IAM role must NOT be able to assume this admin role"

echo "==> Done. Enforcement is now server-side and immutable to the agent."

#!/bin/bash
################################################################################
# 🔧  FIX BRANCH PROTECTION — Replace old checks with current ones              #
################################################################################
set -euo pipefail

OWNER="Digital-Native-Ventures"
REPO="alfred-agent-platform-v2"
BRANCH="main"

# Personal Access Token with `repo` → env var GH_TOKEN
export GH_TOKEN=${GH_TOKEN:-$(gh auth token 2>/dev/null || true)}
[ -z "$GH_TOKEN" ] && { echo "❌  gh auth login first (or set GH_TOKEN)"; exit 1; }

# Get current successful checks on main
SHA=$(gh api repos/$OWNER/$REPO/commits/$BRANCH --jq .sha)
echo "🔍  Current commit SHA: $SHA"

# Get all check names (not just successful ones) to see what's available
echo -e "\n📋  All available checks on main:"
ALL_CHECKS=$(gh api repos/$OWNER/$REPO/commits/$SHA/check-runs \
  --jq '.check_runs[] | .name' | sort -u)
echo "$ALL_CHECKS"

# Define the core checks we want to require
# Based on the actual checks running, we'll require the key ones
CORE_CHECKS=(
  "unit (3.11)"
  "tests"
  "smoke-health"
  "postgres-security-check"
  "template-lint"
  "cve-gate"
)

# Convert to JSON array
NEW_GATES=$(printf '%s\n' "${CORE_CHECKS[@]}" | jq -R . | jq -cs '.')

echo -e "\n✅  Will require these gates:"
echo "$NEW_GATES" | jq -r '.[]'

# Build full JSON body for branch protection
jq -n --argjson ctx "$NEW_GATES" '{
  required_status_checks: { 
    strict: true, 
    contexts: $ctx 
  },
  enforce_admins: false,
  required_pull_request_reviews: {
    required_approving_review_count: 1,
    dismiss_stale_reviews: true,
    require_code_owner_reviews: false,
    require_last_push_approval: false
  },
  restrictions: null,
  allow_force_pushes: false,
  allow_deletions: false,
  block_creations: false,
  required_conversation_resolution: false,
  lock_branch: false,
  allow_fork_syncing: true
}' > /tmp/protect.json

# Update branch protection
echo -e "\n🔒  Updating branch protection..."
gh api --method PUT \
  "repos/$OWNER/$REPO/branches/$BRANCH/protection" \
  --input /tmp/protect.json

echo -e "\n🎉  Branch protection updated! Required checks:"
printf '%s\n' "${CORE_CHECKS[@]}"
echo -e "\nThe old 'ci-summary' check has been removed."
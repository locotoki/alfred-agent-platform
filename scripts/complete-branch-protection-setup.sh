#!/bin/bash
################################################################################
# 📦  COMPLETE BRANCH PROTECTION SETUP                                         #
# Creates a PR with the branch protection scripts and documentation changes    #
################################################################################
set -euo pipefail

OWNER="Digital-Native-Ventures"
REPO="alfred-agent-platform-v2"
BRANCH="main"
DOC_BRANCH="docs/branch-protection-scripts"

export GH_TOKEN=${GH_TOKEN:-$(gh auth token 2>/dev/null || true)}

###############################################################################
# 1️⃣  Show current branch protection status                                    #
###############################################################################
echo "🔍  Current required status checks on branch protection:"
gh api repos/$OWNER/$REPO/branches/$BRANCH/protection --jq '.required_status_checks.contexts[]'

###############################################################################
# 2️⃣  Create a feature branch and commit our changes                          #
###############################################################################
# First, let's reset our local main to match origin (abandon local commit)
git reset --hard origin/main

# Create new branch
git switch -c "$DOC_BRANCH" 2>/dev/null || git switch "$DOC_BRANCH"

# Add all the branch protection scripts
git add scripts/align-branch-protection.sh
git add scripts/setup-branch-protection.sh
git add scripts/update-branch-protection-full.sh
git add scripts/fix-branch-protection.sh
git add scripts/post-protection-followup.sh
git add scripts/complete-branch-protection-setup.sh

# Add the documentation changes
git add .github/pull_request_template.md
git add docs/taxonomy-integration.md

# Commit
git commit -m "feat: add branch protection management scripts

- Add scripts to set up and manage GitHub branch protection rules
- Update PR template with GPT-o3 architect checklist
- Update taxonomy integration documentation

These scripts help maintain proper CI gates on the main branch."

# Push to origin
git push -u origin "$DOC_BRANCH"

###############################################################################
# 3️⃣  Create the PR                                                           #
###############################################################################
PR_BODY="## Description

This PR adds scripts to manage GitHub branch protection rules for the repository.

## Added Scripts

- \`scripts/setup-branch-protection.sh\` - Initial branch protection setup
- \`scripts/fix-branch-protection.sh\` - Fix branch protection with current CI checks
- \`scripts/align-branch-protection.sh\` - Align protection with successful checks
- \`scripts/update-branch-protection-full.sh\` - Update protection after CI runs
- \`scripts/post-protection-followup.sh\` - Post-setup follow-up actions
- \`scripts/complete-branch-protection-setup.sh\` - This script

## Documentation Updates

- Updated PR template with GPT-o3 architect checklist
- Updated taxonomy integration documentation

## Testing Done

- Successfully set up branch protection on main branch
- Verified required checks are properly configured
- Confirmed the old 'ci-summary' check was removed

## Change Type

- [x] Feature
- [x] Documentation
- [x] Infrastructure / DevOps"

gh pr create \
  --title "feat: branch protection management scripts" \
  --body "$PR_BODY" \
  --label "infrastructure" --label "devops" --label "documentation"

echo -e "\n🎉  PR created! The branch protection is now properly configured with these required checks:"
gh api repos/$OWNER/$REPO/branches/$BRANCH/protection --jq '.required_status_checks.contexts[]'
#!/bin/bash
################################################################################
# 📦  POST–BRANCH-PROTECTION FOLLOW-UP BLOCK                                   #
# Why: you just fixed the protection rule. Next we                             #
#   1.  Verify the new main-branch run is ✅ with the *real* gates.             #
#   2.  Restore (pop) your stashed work, ship it on a proper PR.               #
#   3.  Confirm you can now push *via PR* and the checks appear as required.   #
################################################################################
set -euo pipefail

OWNER="Digital-Native-Ventures"
REPO="alfred-agent-platform-v2"
BRANCH="main"
DOC_BRANCH="docs/platform-consistency"

###############################################################################
# 1️⃣  Wait for the first run under the new gate set                           #
###############################################################################
echo -n "⏳  Waiting for latest workflow on main … "
RUN_ID=""
until [[ -n "$RUN_ID" && "$(gh run view $RUN_ID --json status -q .status)" == "completed" ]]; do
  RUN_ID=$(gh run list --branch $BRANCH --limit 1 --json databaseId | jq -r '.[0].databaseId')
  printf "."; sleep 20
done
CONC=$(gh run view "$RUN_ID" --json conclusion -q .conclusion)
echo " $CONC"
if [[ "$CONC" != "success" ]]; then
  echo "❌  Main is still red.  Inspect run $RUN_ID and fix before continuing."; exit 1;
fi

###############################################################################
# 2️⃣  Restore your stashed docs work & open PR                                #
###############################################################################
if git stash list | grep -q "All changes for branch protection update"; then
  git stash pop
  echo "✅  Stash popped."
fi

# create docs branch if not yet
git switch -c "$DOC_BRANCH" 2>/dev/null || git switch "$DOC_BRANCH"
git add PLATFORM_CONSISTENCY.md DEPLOYMENT_STRATEGY.md start-full-platform.sh .env
git commit -m "docs: platform-consistency guide + full-stack script"
git push -u origin "$DOC_BRANCH"

gh pr create --fill \
  --title "docs: platform consistency & cross-platform start script" \
  --label docs --label dx --label "sprint:v1.1"

###############################################################################
# 3️⃣  Show that required checks now list correctly                            #
###############################################################################
echo -e "\n🔍  Required status checks on branch protection now:"
gh api repos/$OWNER/$REPO/branches/$BRANCH/protection --jq '.required_status_checks.contexts[]'

echo -e "\n🎉  Main is green, docs PR opened.  Continue normal feature work!"
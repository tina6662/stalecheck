#!/bin/sh
# End-to-end demo in a throwaway copy: write the paper, change the analysis, catch what went stale.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PYTHON:-python3}
WORK=$(mktemp -d)
cp "$HERE/analysis.py" "$HERE/data.csv" "$HERE/paper.md" "$HERE/paper.tex" "$WORK"
cd "$WORK"
git init -q && git config user.name demo && git config user.email demo@example.com
mkdir .stalecheck

step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "1. Run the analysis; the paper was written from these numbers"
git add . && git commit -qm "initial analysis"
$PY analysis.py
git add .stalecheck && git commit -qm "results v1"
$PY -m stalecheck check -v paper.md paper.tex

step "2. Reviewer asks us to drop participants who failed the attention check"
sed -i.bak 's/= False  # the demo/= True  # the demo/' analysis.py && rm analysis.py.bak
git commit -qam "exclude failed attention checks"
$PY analysis.py

step "3. Which numbers in the paper are now wrong?"
$PY -m stalecheck check --scan paper.md paper.tex || true

step "4. Where did the slope change?"
$PY -m stalecheck trace slope paper.md paper.tex

step "5. Fix tagged numbers automatically (formatting preserved)"
$PY -m stalecheck fix --write paper.md paper.tex

step "6. What is left needs judgement (untagged numbers in the abstract)"
$PY -m stalecheck check --scan paper.md paper.tex || true

echo "\n(work dir: $WORK)"

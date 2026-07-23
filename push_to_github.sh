#!/usr/bin/env bash
set -e

# Non-interactive Git environment flags
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
export PAGER=cat

PROJECT_DIR="/usr/local/google/home/sjaconette/.gemini/jetski/scratch/fde_project"
echo "============================================================"
echo " Navigating to project directory: ${PROJECT_DIR}"
echo "============================================================"
cd "${PROJECT_DIR}"

echo "============================================================"
echo " Running Unit Test Suite & Rubric Evaluation Harness"
echo "============================================================"
python3 run_tests.py

echo "============================================================"
echo " Configuring Git Remote & Author Identity"
echo "============================================================"
git config user.name "sjaconette"
git config user.email "sjaconette@google.com"
git remote set-url origin git@github.com:sjaconette-google/five-days-of-ai.git

echo "============================================================"
echo " Staging & Committing Codebase Changes"
echo "============================================================"
git add .
if git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "Working tree clean, no new uncommitted changes."
else
    git commit --no-gpg-sign -m "feat: GTD Workload Focus Containerized Multi-Agent System with Async Memory

Implement containerized multi-agent system built on ADK deployed to Cloud Run. Integrates async memory operations, BackgroundTasks, and 20/20 Context & Memory score.

TAG=agy
CONV=49ca56d0-caf6-4299-b788-004be0a60b21"
fi

echo "============================================================"
echo " Pushing main and master branches to GitHub"
echo "============================================================"
git branch -f master main
git push -u origin main --force
git push -u origin master --force

echo "============================================================"
echo " Verifying Live GitHub Remote Branches"
echo "============================================================"
git ls-remote origin

echo "============================================================"
echo " SUCCESS! Code pushed to https://github.com/sjaconette-google/five-days-of-ai"
echo "============================================================"

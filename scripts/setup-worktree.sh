#!/usr/bin/env bash
# Prepares a git worktree for an agent. Run from inside the new worktree with
# ROOT_WORKTREE_PATH set to the main checkout. Safe to run before the app exists.
set -euo pipefail

ROOT="${ROOT_WORKTREE_PATH:?ROOT_WORKTREE_PATH must point to the main checkout}"

# .env files are git-ignored, so copy them from the main checkout.
for env_file in backend/.env frontend/.env.local frontend/.env; do
  if [ -f "$ROOT/$env_file" ] && [ ! -f "$env_file" ]; then
    cp "$ROOT/$env_file" "$env_file"
  fi
done

PYTHON_BIN="$(command -v python3.12 || command -v python3)"
if [ -f backend/requirements.txt ]; then
  "$PYTHON_BIN" -m venv backend/.venv
  backend/.venv/bin/pip install --quiet --disable-pip-version-check -r backend/requirements.txt
  if [ -f backend/requirements-dev.txt ]; then
    backend/.venv/bin/pip install --quiet --disable-pip-version-check -r backend/requirements-dev.txt
  fi
fi

if [ -f frontend/package-lock.json ]; then
  (cd frontend && npm ci --silent)
elif [ -f frontend/package.json ]; then
  (cd frontend && npm install --silent)
fi

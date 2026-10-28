#!/usr/bin/env bash
# One-time: turn /opt/clinic-crm into a git checkout of the GitHub repo.
set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/Narayanan960080/clinic-crm.git}"
APP_DIR="${APP_DIR:-/opt/clinic-crm}"
BRANCH="${BRANCH:-main}"

if [ "$(id -u)" -ne 0 ] && [ ! -w "$APP_DIR" ]; then
  echo "Run with sudo or as a user that can write $APP_DIR"
  exit 1
fi

mkdir -p "$APP_DIR"
cd "$APP_DIR"

if [ -d .git ]; then
  git remote set-url origin "$REPO_URL" || git remote add origin "$REPO_URL"
else
  git init -b "$BRANCH"
  git remote add origin "$REPO_URL"
fi

git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"
chmod +x scripts/deploy.sh 2>/dev/null || true
echo "Git checkout ready at $APP_DIR on origin/$BRANCH"

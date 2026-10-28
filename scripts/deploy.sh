#!/usr/bin/env bash
# Run on the GCP VM after git is wired to GitHub (see docs/CICD.md).
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/clinic-crm}"
cd "$APP_DIR"
git fetch origin main
git reset --hard origin/main
docker compose build api
docker compose up -d
docker compose ps

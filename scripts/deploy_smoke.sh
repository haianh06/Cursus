#!/usr/bin/env bash
# Smoke-check a running Cursus stack.
# Usage:
#   ./scripts/deploy_smoke.sh
#   API_BASE=http://127.0.0.1:8000 WEB_BASE=http://127.0.0.1:3000 ./scripts/deploy_smoke.sh
#   EMAIL=student.demo@example.test PASSWORD=password123 ./scripts/deploy_smoke.sh

set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
WEB_BASE="${WEB_BASE:-http://127.0.0.1:3000}"

echo "Checking backend health at ${API_BASE}/health ..."
curl -fsS "${API_BASE}/health" | grep -q '"status"'

echo "Checking frontend at ${WEB_BASE}/ ..."
curl -fsS -o /dev/null "${WEB_BASE}/"

if [[ -n "${EMAIL:-}" && -n "${PASSWORD:-}" ]]; then
  echo "Checking login ..."
  curl -fsS -X POST "${API_BASE}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"remember_me\":true}" \
    | grep -q '"user"'
else
  echo "SKIP auth login (set EMAIL and PASSWORD to enable)"
fi

echo "Smoke checks passed."

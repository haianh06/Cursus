#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

python scripts/seed_courses.py
python scripts/seed_assignments.py
python scripts/seed_curriculum.py
python scripts/seed_syllabi_from_chunks.py
python scripts/ensure_oauth_client.py

exec uvicorn app.main:app --host 0.0.0.0 --port 9000

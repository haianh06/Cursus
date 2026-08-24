#!/usr/bin/env bash
# Cai dat va kiem tra AI Log Bridge — mot lenh duy nhat.
#
#   bash tools/ai-log-extension/setup.sh            cai + kiem tra
#   bash tools/ai-log-extension/setup.sh --check    chi kiem tra
#   bash tools/ai-log-extension/setup.sh --server   kiem tra ca grading server
#
# Wrapper chi lo tim Python — moi logic nam trong setup.py.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

PY=""
for cand in "$REPO/.venv/bin/python" "$REPO/.venv/Scripts/python.exe"; do
  [ -x "$cand" ] && { PY="$cand"; break; }
done
[ -n "$PY" ] || PY="$(command -v python3 || command -v python || true)"
[ -n "$PY" ] || { echo "Khong tim thay Python. Cai Python roi chay lai." >&2; exit 1; }

exec "$PY" "$HERE/setup.py" "$@"

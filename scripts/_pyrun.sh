#!/usr/bin/env bash
# Cross-platform Python launcher for AI log hooks.
# Tries the local .venv python first, then python3 → python → py -3 on PATH.
# On Windows, falls back to common Python install locations.
# Designed to be sourced or called as: bash scripts/_pyrun.sh <script> [args...]
#
# Exits 0 silently if no Python is found — hooks must never block the AI tool.
set -u

# Check if .venv python exists in the workspace
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

PY=""
if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  PY="$REPO_ROOT/.venv/bin/python"
elif [ -x "$REPO_ROOT/.venv/Scripts/python" ]; then
  PY="$REPO_ROOT/.venv/Scripts/python"
elif [ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]; then
  PY="$REPO_ROOT/.venv/Scripts/python.exe"
fi

if [ -z "$PY" ]; then
  # Windows Store publishes broken "python"/"python3" alias stubs under
  # WindowsApps that print an install prompt and do nothing useful — skip them.
  _is_store_stub() {
    case "$1" in
      */WindowsApps/*) return 0 ;;
      *) return 1 ;;
    esac
  }

  for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
      resolved=$(command -v "$cand")
      if ! _is_store_stub "$resolved"; then
        PY="$cand"
        break
      fi
    fi
  done

  if [ -z "$PY" ] && command -v py >/dev/null 2>&1; then
    PY="py -3"
  fi

  if [ -z "$PY" ]; then
    # PATH lookup failed — probe standard Windows install locations.
    shopt -s nullglob 2>/dev/null || true
    for cand in \
      /c/Users/*/AppData/Local/Programs/Python/Python*/python.exe \
      "/c/Program Files/Python"*/python.exe \
      "/c/Program Files (x86)/Python"*/python.exe \
      /c/Python*/python.exe; do
      if [ -x "$cand" ]; then PY="$cand"; break; fi
    done
    shopt -u nullglob 2>/dev/null || true
  fi
fi

[ -n "$PY" ] || exit 0

# $PY must stay quoted: the .venv path can sit under a directory with spaces
# (e.g. "1.Chuyen Nganh"), and a bare $PY word-splits there, so the hook dies
# with exit 127 and silently logs nothing. "py -3" is the only multi-word value
# we ever set, so split that one case explicitly instead of unquoting $PY.
if [ "$PY" = "py -3" ]; then
  exec py -3 "$@"
fi
exec "$PY" "$@"

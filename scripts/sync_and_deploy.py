"""Mirror source code from the Cursus dev repo into this deploy repo
(Cursus_demo), then auto commit + push + deploy on every change.

Source of truth for "what counts as source" is git itself: for each repo,
`git ls-files --cached --others --exclude-standard` lists every tracked file
plus every untracked-but-not-gitignored file. That set naturally excludes
node_modules/, .venv/, dist/, data/, __pycache__/, .env, etc. (already
gitignored in both repos) without hardcoding a big exclude list here.

A short list of paths that belong to THIS deploy repo only (render.yaml,
vercel.json, DEPLOY.md, scripts/sql/*, .env, .git, .claude/, supabase/, and
this script itself) is never touched, even if Cursus has a file at the same
path.

Usage:
    python scripts/sync_and_deploy.py           # watch loop, Ctrl+C to stop
    python scripts/sync_and_deploy.py --once     # single pass, no loop

Every pass that finds changes: copies/deletes files in Cursus_demo to mirror
Cursus, `git add -A && git commit && git push origin main`, then triggers a
Render deploy (if backend files changed) and/or `vercel --prod` (if
frontend/ files changed). No confirmation prompt -- this pushes straight to
production on every detected change, by explicit request.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from pathlib import Path

SOURCE = Path(r"C:\Document\AIinAction\Cursus")
DEST = Path(r"C:\Document\AIinAction\Cursus_demo")

RENDER_SERVICE_ID = "srv-da6502u7bikc73asot40"
GIT_BRANCH = "main"
POLL_SECONDS = 5
DEBOUNCE_SECONDS = 8

# Relative paths (forward-slash, relative to repo root) that belong to this
# deploy repo only and must never be overwritten or deleted by the sync.
DEPLOY_ONLY_PATHS = {
    ".git",
    ".env",
    ".gitignore",
    "render.yaml",
    "frontend/vercel.json",
    "frontend/.gitignore",
    "DEPLOY.md",
    "scripts/sync_and_deploy.py",
}
DEPLOY_ONLY_PREFIXES = ("scripts/sql/", ".claude/", "supabase/", "frontend/.vercel/")

# Belt-and-suspenders: excluded from `git add -A` by pathspec too, so a
# machine-local dir that isn't (yet) gitignored can never be committed even
# if the mirror step above is bypassed or a new one shows up unaccounted for.
GIT_ADD_EXCLUDE_PATHSPECS = [":(exclude)" + p for p in (".claude", "supabase")]


def _is_deploy_only(rel_path: str) -> bool:
    if rel_path in DEPLOY_ONLY_PATHS:
        return True
    return any(rel_path.startswith(prefix) for prefix in DEPLOY_ONLY_PREFIXES)


def _tracked_files(repo: Path) -> set[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True, text=True, check=True,
    ).stdout
    return {line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()}


def _signature(repo: Path, files: set[str]) -> tuple:
    sig = []
    for rel in sorted(files):
        try:
            st = (repo / rel).stat()
            sig.append((rel, st.st_size, int(st.st_mtime)))
        except FileNotFoundError:
            sig.append((rel, -1, -1))
    return tuple(sig)


def sync_once(log) -> list[str]:
    """Mirror SOURCE -> DEST. Returns the list of changed relative paths."""
    source_files = _tracked_files(SOURCE)
    dest_files = _tracked_files(DEST)

    wanted = {f for f in source_files if not _is_deploy_only(f)}
    existing_synced = {f for f in dest_files if not _is_deploy_only(f)}

    changed: list[str] = []
    new_migrations: list[str] = []

    for rel in sorted(wanted):
        src_path, dst_path = SOURCE / rel, DEST / rel
        if not src_path.is_file():
            continue
        needs_copy = True
        if dst_path.exists():
            s_st, d_st = src_path.stat(), dst_path.stat()
            needs_copy = not (s_st.st_size == d_st.st_size and int(s_st.st_mtime) == int(d_st.st_mtime))
        if needs_copy:
            was_new = not dst_path.exists()
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            changed.append(rel)
            log(f"  copy: {rel}")
            if was_new and rel.startswith("migrations/versions/"):
                new_migrations.append(rel)

    deleted_dirs: set[Path] = set()
    for rel in sorted(existing_synced - wanted):
        dst_path = DEST / rel
        if dst_path.exists():
            dst_path.unlink()
            changed.append(rel)
            log(f"  delete: {rel}")
            deleted_dirs.add(dst_path.parent)

    for start_dir in sorted(deleted_dirs, key=lambda p: -len(str(p))):
        d = start_dir
        while d != DEST and d.exists():
            try:
                next(d.iterdir())
                break
            except StopIteration:
                d.rmdir()
                d = d.parent
            except OSError:
                break

    if new_migrations:
        log("  [!] migration moi phat hien -- tu doi chieu/chay tay tren Supabase Dashboard (docs/PROJECT_CONTEXT.md muc 20 y8):")
        for m in new_migrations:
            log(f"      {m}")

    return changed


def run_pipeline(log) -> None:
    changed = sync_once(log)
    if not changed:
        log("  khong co gi thay doi.")
        return

    subprocess.run(
        ["git", "-C", str(DEST), "add", "-A", "--", "."] + GIT_ADD_EXCLUDE_PATHSPECS, check=True
    )
    already_clean = subprocess.run(
        ["git", "-C", str(DEST), "diff", "--cached", "--quiet"]
    ).returncode == 0
    if already_clean:
        log("  khong co gi de commit (chi dung file bi loai tru?) -- bo qua deploy.")
        return

    msg = f"sync: mirror from Cursus dev repo (auto, {time.strftime('%Y-%m-%d %H:%M:%S')})"
    subprocess.run(["git", "-C", str(DEST), "commit", "-m", msg], check=True)

    push = subprocess.run(["git", "-C", str(DEST), "push", "origin", GIT_BRANCH])
    if push.returncode != 0:
        log("  [x] git push THAT BAI -- khong trigger deploy. Xu ly xung dot roi chay lai (--once).")
        return
    log(f"  [ok] da push len origin/{GIT_BRANCH}")

    touches_frontend = any(p.startswith("frontend/") for p in changed)
    touches_backend = any(not p.startswith("frontend/") for p in changed)

    if touches_backend:
        render_cli = shutil.which("render")
        if render_cli is None:
            log("  [x] khong tim thay 'render' CLI trong PATH -- bo qua render deploy.")
        else:
            r = subprocess.run(
                [render_cli, "deploys", "create", RENDER_SERVICE_ID, "--confirm", "--output", "json"],
                capture_output=True, text=True,
            )
            log("  render deploy: " + ("OK" if r.returncode == 0 else f"LOI: {r.stderr[:300]}"))

    if touches_frontend:
        vercel_cli = shutil.which("vercel")
        if vercel_cli is None:
            log("  [x] khong tim thay 'vercel' CLI trong PATH -- bo qua vercel deploy.")
        else:
            r = subprocess.run(
                [vercel_cli, "--prod", "--yes"], cwd=str(DEST / "frontend"),
                capture_output=True, text=True,
            )
            log("  vercel deploy: " + ("OK" if r.returncode == 0 else f"LOI: {r.stderr[:300]}"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="chay 1 lan roi thoat, khong watch")
    args = parser.parse_args()

    def log(msg: str) -> None:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    if args.once:
        run_pipeline(log)
        return

    log(f"Theo doi {SOURCE} -> tu sync + deploy vao {DEST}")
    log(f"(poll {POLL_SECONDS}s, debounce {DEBOUNCE_SECONDS}s -- Ctrl+C de dung)")

    last_sig = None
    stable_since = None
    while True:
        try:
            files = _tracked_files(SOURCE)
            sig = _signature(SOURCE, files)
        except subprocess.CalledProcessError as exc:
            log(f"  [x] loi doc repo nguon: {exc}")
            time.sleep(POLL_SECONDS)
            continue

        if sig != last_sig:
            last_sig = sig
            stable_since = time.time()
        elif stable_since is not None and time.time() - stable_since >= DEBOUNCE_SECONDS:
            stable_since = None
            log("Phat hien thay doi & da on dinh -- dang sync...")
            try:
                run_pipeline(log)
            except subprocess.CalledProcessError as exc:
                log(f"  [x] loi pipeline: {exc}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Native messaging host: answers git questions the browser cannot.

The extension has no filesystem access, so the closest it can otherwise get to
"which commit was I on?" is the newest commit GitHub has — which misses
anything unpushed. This host runs the same `git` commands log_hook.py runs, so
the two agree exactly.

Wire format (Chrome native messaging):
  stdin/stdout carry a 4-byte native-order length followed by UTF-8 JSON.

Requests:
  {"action": "ping"}
  {"action": "repoinfo", "repo": "<optional path, else the configured default>"}

Never writes anything to stdout except a framed reply — a stray print corrupts
the stream and the extension sees the host as crashed.
"""
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

VERSION = "1.1.0"
NOT_A_REPO = ("Đường dẫn không phải gốc của một git repo. "
              "Trỏ đúng thư mục chứa .git (kiểm tra host_config.json).")
HERE = Path(__file__).resolve().parent
CONFIG_FILE = HERE / "host_config.json"
LOG_FILE = HERE / "host.log"

# Chrome caps a message from the extension at 1 MB.
MAX_MESSAGE = 1024 * 1024


def log(message: str) -> None:
    """Debug trail. Only written when host_config.json sets debug=true, because
    a native host that silently grows a log file is its own kind of bug."""
    try:
        if not _config().get("debug"):
            return
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message.rstrip() + "\n")
    except Exception:
        pass


_config_cache = None


def _config() -> dict:
    global _config_cache
    if _config_cache is None:
        try:
            # utf-8-sig, not utf-8: a config written by PowerShell's
            # Set-Content -Encoding utf8 starts with a BOM, and plain utf-8
            # makes json.loads die on the very first character — after which
            # the host silently behaves as if it were never configured.
            _config_cache = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
        except Exception:
            _config_cache = {}
    return _config_cache


def read_message():
    """Return the next request, or None at end of stream."""
    raw_len = sys.stdin.buffer.read(4)
    if len(raw_len) < 4:
        return None
    (length,) = struct.unpack("@I", raw_len)
    if length == 0 or length > MAX_MESSAGE:
        return None
    body = sys.stdin.buffer.read(length)
    if len(body) < length:
        return None
    return json.loads(body.decode("utf-8"))


def write_message(payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("@I", len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def git(args, cwd):
    """Run one git command. Returns '' on any failure — callers decide what a
    missing value means rather than getting an exception mid-protocol."""
    try:
        out = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if out.returncode != 0:
            return ""
        return out.stdout.strip()
    except Exception as exc:
        log(f"git {args} failed: {exc}")
        return ""


def _as_repo_root(candidate: str) -> Path | None:
    """Accept only the repo ROOT, not merely somewhere inside a work tree.

    `git rev-parse --is-inside-work-tree` walks upward, so if the user's home
    directory happens to be a git repo — common, dotfiles are often versioned —
    then almost any mistyped path answers "true" and we would cheerfully report
    a completely unrelated project's commit. Requiring toplevel == path makes a
    wrong path fail loudly instead.
    """
    try:
        path = Path(candidate).expanduser().resolve()
    except Exception:
        return None
    if not path.is_dir():
        return None
    toplevel = git(["rev-parse", "--show-toplevel"], path)
    if not toplevel:
        return None
    try:
        if Path(toplevel).resolve() != path:
            log(f"{path} nam trong repo {toplevel}, khong phai goc repo")
            return None
    except Exception:
        return None
    return path


def resolve_repo(requested) -> Path | None:
    """A repo the caller named explicitly must resolve or fail — falling back
    to the installed default would answer a question about repo Y while the
    caller asked about repo X, which is the wrong-commit bug wearing a hat.
    The default applies only when nothing was asked for.
    """
    if isinstance(requested, str) and requested.strip():
        return _as_repo_root(requested.strip())

    configured = _config().get("repo")
    if isinstance(configured, str) and configured.strip():
        return _as_repo_root(configured.strip())
    return None


def _ahead_behind(repo_path, ref: str, upstream: str):
    """(ahead, behind) of ref relative to its upstream, as strings."""
    if not upstream:
        return "", ""
    counts = git(["rev-list", "--left-right", "--count", f"{upstream}...{ref}"], repo_path)
    parts = counts.split()
    if len(parts) != 2:
        return "", ""
    behind, ahead = parts  # left is upstream-only, right is ref-only
    return ahead, behind


def branch_list(requested) -> dict:
    """Every local branch with its own commit and how far it is from its remote.

    The extension used to take the branch name as free text, so a typo silently
    produced the wrong commit — or none. Handing back the real list turns that
    into a dropdown that cannot be misspelled.
    """
    repo_path = resolve_repo(requested)
    if repo_path is None:
        return {"ok": False, "error": NOT_A_REPO}

    current = git(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)
    fmt = "%(refname:short)%09%(objectname:short)%09%(objectname)%09%(upstream:short)%09%(contents:subject)"
    raw = git(["for-each-ref", "--format=" + fmt, "refs/heads"], repo_path)

    branches = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        name, short, full, upstream, subject = parts[0], parts[1], parts[2], parts[3], parts[4]
        ahead, behind = _ahead_behind(repo_path, name, upstream)
        branches.append({
            "name": name,
            "commit": short,
            "full": full,
            "upstream": upstream,
            "ahead": ahead,
            "behind": behind,
            "message": subject[:120],
            "current": name == current,
        })

    return {"ok": True, "current": current, "branches": branches, "version": VERSION}


def repo_info(requested, branch=None) -> dict:
    repo_path = resolve_repo(requested)
    if repo_path is None:
        return {"ok": False, "error": NOT_A_REPO}

    root = git(["rev-parse", "--show-toplevel"], repo_path) or str(repo_path)
    current = git(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)

    # A pinned branch reports that branch's tip; otherwise follow HEAD.
    wanted = branch.strip() if isinstance(branch, str) and branch.strip() else ""
    if wanted and wanted != current:
        if git(["rev-parse", "--verify", "--quiet", "refs/heads/" + wanted], repo_path) == "":
            return {"ok": False, "error": f"Không có branch '{wanted}' trong repo."}
        ref = wanted
    else:
        ref = "HEAD"

    branch = wanted or current
    full = git(["rev-parse", ref], repo_path)
    short = git(["rev-parse", "--short", ref], repo_path)
    student = git(["config", "user.email"], repo_path)
    subject = git(["log", "-1", "--pretty=%s", ref], repo_path)

    # Same derivation log_hook.py uses, so the repo name matches what the
    # server already has on file for this team.
    origin = git(["remote", "get-url", "origin"], repo_path)
    repo_name = ""
    if origin:
        repo_name = origin.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

    # Uncommitted work is exactly the thing the GitHub API can never see.
    # Only meaningful for HEAD — a pinned other branch is not checked out.
    dirty = bool(git(["status", "--porcelain"], repo_path)) if ref == "HEAD" else False

    upstream = git(["rev-parse", "--abbrev-ref", branch + "@{upstream}"], repo_path)
    unpushed, behind = _ahead_behind(repo_path, branch, upstream)

    return {
        "ok": True,
        "root": root,
        "repo": repo_name,
        "origin": origin,
        "branch": branch,
        "current_branch": current,
        "pinned": bool(wanted),
        "commit": short,
        "full": full,
        "message": subject[:120],
        "student": student,
        "dirty": dirty,
        "upstream": upstream,
        "unpushed": unpushed,
        "behind": behind,
        "version": VERSION,
    }


def handle(msg: dict) -> dict:
    msg = msg or {}
    action = msg.get("action")
    if action == "ping":
        return {"ok": True, "version": VERSION}
    if action == "repoinfo":
        return repo_info(msg.get("repo"), msg.get("branch"))
    if action == "branches":
        return branch_list(msg.get("repo"))
    return {"ok": False, "error": f"unknown action: {action!r}"}


def main() -> None:
    # Windows translates \n to \r\n on a text-mode stdout, which corrupts the
    # length-prefixed framing. Force binary before writing anything.
    if sys.platform == "win32":
        import msvcrt

        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)

    while True:
        try:
            msg = read_message()
        except Exception as exc:
            log(f"read failed: {exc}")
            return
        if msg is None:
            return
        try:
            reply = handle(msg)
        except Exception as exc:
            log(f"handle failed: {exc}")
            reply = {"ok": False, "error": str(exc)}
        try:
            write_message(reply)
        except Exception as exc:
            log(f"write failed: {exc}")
            return


if __name__ == "__main__":
    main()

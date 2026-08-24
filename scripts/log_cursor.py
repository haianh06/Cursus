#!/usr/bin/env python3
"""
Cursor transcript log scanner — extracts exact user prompts from local Cursor
agent transcripts and appends them to .ai-log/session.jsonl.

Source of truth:
    ~/.cursor/projects/<project>/agent-transcripts/<conv_id>/<conv_id>.jsonl

Each transcript line is a JSON object. We emit one log entry per line where
`role == "user"`. The text inside <user_query>...</user_query> is the exact
prompt the user typed. If no wrapper exists, known metadata blocks are stripped
and the remaining text is logged.

Usage:
  python scripts/log_cursor.py --auto            # default: last 24h
  python scripts/log_cursor.py --hours 72
  python scripts/log_cursor.py --all             # every conv, no cutoff
  python scripts/log_cursor.py --conv-id <id>    # one conversation
  python scripts/log_cursor.py --dry-run         # preview only

Env overrides:
  CURSOR_PROJECTS_DIR      point at ~/.cursor/projects
  CURSOR_TRANSCRIPTS_DIR   point directly at one agent-transcripts directory
  AI_LOG_DIR               where session.jsonl is written (default: .ai-log)
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VN_TZ = timezone(timedelta(hours=7))
CURSOR_HOME = Path.home() / ".cursor"
PROJECTS_DIR = Path(os.environ.get("CURSOR_PROJECTS_DIR", CURSOR_HOME / "projects"))

USER_QUERY_RE = re.compile(r"<user_query>(.*?)</user_query>", re.DOTALL | re.I)
TIMESTAMP_RE = re.compile(r"<timestamp>(.*?)</timestamp>", re.DOTALL | re.I)
AUX_BLOCK_RE = re.compile(
    r"<(?:open_and_recently_viewed_files|attached_files|system_reminder|rules|user_info)>"
    r".*?"
    r"</(?:open_and_recently_viewed_files|attached_files|system_reminder|rules|user_info)>",
    re.DOTALL | re.I,
)

# Cursor's <timestamp> is human-readable, e.g. "Tuesday, Aug 4, 2026, 8:24 PM (UTC+7)".
CURSOR_TS_RE = re.compile(
    r"^\w+,\s*(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2}),\s*(?P<year>\d{4}),\s*"
    r"(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<ampm>AM|PM)\s*\(UTC(?P<offset>[+-]?\d+)\)$"
)
MONTH_ABBR = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def git(cmd: str) -> str:
    try:
        return subprocess.check_output(
            cmd.split(),
            shell=False,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ""


def get_transcript_roots(repo_root: Path) -> list[Path]:
    env = os.environ.get("CURSOR_TRANSCRIPTS_DIR")
    if env:
        root = Path(env)
        return [root] if root.exists() else []

    project_dir = PROJECTS_DIR / _cursor_project_slug(repo_root)
    roots: list[Path] = []
    direct = project_dir / "agent-transcripts"
    if direct.exists():
        roots.append(direct)

    if not PROJECTS_DIR.exists():
        return roots

    for candidate in PROJECTS_DIR.glob("*/agent-transcripts"):
        if candidate not in roots:
            roots.append(candidate)
    return roots


def _cursor_project_slug(repo_root: Path) -> str:
    resolved = repo_root.resolve()
    raw = str(resolved).replace(":", "")
    return re.sub(r"[^A-Za-z0-9]+", "-", raw).strip("-")


def get_logged_entry_ids(log_file: Path) -> set[str]:
    logged: set[str] = set()
    if not log_file.exists():
        return logged
    with open(log_file, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            entry_id = entry.get("entry_id", "")
            if entry_id:
                logged.add(entry_id)
    return logged


def iter_transcripts(
    roots: list[Path],
    only_conv: str | None,
    repo_slug: str,
    no_repo_filter: bool,
):
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for transcript in root.glob("*/*.jsonl"):
            if transcript in seen:
                continue
            seen.add(transcript)
            conv_id = transcript.stem
            if only_conv and conv_id != only_conv:
                continue
            if not no_repo_filter and repo_slug.lower() not in str(transcript).lower():
                continue
            yield transcript


def iter_user_inputs(
    roots: list[Path],
    cutoff: datetime | None,
    only_conv: str | None,
    repo_slug: str,
    no_repo_filter: bool,
):
    for transcript in iter_transcripts(roots, only_conv, repo_slug, no_repo_filter):
        with open(transcript, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("role") != "user":
                    continue

                content = entry.get("message", {}).get("content", [])
                text = _content_to_text(content)
                prompt = extract_user_prompt(text)
                if len(prompt) < 2:
                    continue

                ts = extract_timestamp(text)
                if cutoff and ts:
                    normalized = normalize_timestamp(ts)
                    if normalized:
                        try:
                            ts_dt = datetime.fromisoformat(normalized)
                            if ts_dt < cutoff:
                                continue
                        except ValueError:
                            pass

                yield {
                    "conv_id": transcript.stem,
                    "line_no": line_no,
                    "timestamp": ts,
                    "text": prompt,
                }


def _content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    chunks: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            chunks.append(str(item.get("text", "")))
    return "\n".join(chunks)


def extract_user_prompt(content: str) -> str:
    match = USER_QUERY_RE.search(content)
    if match:
        return match.group(1).strip()
    cleaned = TIMESTAMP_RE.sub("", content)
    cleaned = AUX_BLOCK_RE.sub("", cleaned)
    return cleaned.strip()


def extract_timestamp(content: str) -> str:
    match = TIMESTAMP_RE.search(content)
    if match:
        return match.group(1).strip()
    return ""


def _parse_cursor_timestamp(ts: str) -> datetime | None:
    """Parse Cursor's human-readable timestamp into an aware datetime."""
    match = CURSOR_TS_RE.match(ts.strip())
    if not match:
        return None

    month = MONTH_ABBR.get(match.group("month")[:3].title())
    if not month:
        return None

    hour = int(match.group("hour")) % 12
    if match.group("ampm").upper() == "PM":
        hour += 12

    tz = timezone(timedelta(hours=int(match.group("offset"))))
    try:
        return datetime(
            int(match.group("year")),
            month,
            int(match.group("day")),
            hour,
            int(match.group("minute")),
            tzinfo=tz,
        )
    except ValueError:
        return None


def normalize_timestamp(ts: str) -> str:
    """Convert a Cursor timestamp to the same ISO 8601 `ts` format used by
    log_antigravity.py, e.g. "2026-08-04T20:24:00+07:00"."""
    if not ts:
        return ""

    parsed = _parse_cursor_timestamp(ts)
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return ""

    return parsed.astimezone(VN_TZ).isoformat()


def build_entry(
    msg: dict,
    repo: str,
    branch: str,
    commit: str,
    student: str,
) -> dict:
    return {
        "ts": normalize_timestamp(msg["timestamp"]) or datetime.now(VN_TZ).isoformat(),
        "tool": "cursor",
        "event": "UserPrompt",
        "entry_id": f"cursor-{msg['conv_id']}-{msg['line_no']:05d}",
        "session_id": msg["conv_id"],
        "model": "cursor",
        "repo": repo,
        "branch": branch,
        "commit": commit,
        "student": student,
        "prompt": msg["text"][:1000],
        "response_summary": "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract user prompts from Cursor transcripts into .ai-log/session.jsonl."
    )
    parser.add_argument("--auto", action="store_true", help="Scan recent conversations.")
    parser.add_argument("--hours", type=int, default=24, help="Window in hours.")
    parser.add_argument("--all", action="store_true", help="Ignore the time window.")
    parser.add_argument("--conv-id", help="Limit to one conversation id.")
    parser.add_argument(
        "--no-repo-filter",
        action="store_true",
        help="Don't filter conversations by current repo/project folder.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only.")
    args = parser.parse_args()

    repo_root = Path.cwd()
    repo_slug = _cursor_project_slug(repo_root)
    roots = get_transcript_roots(repo_root)
    if not roots:
        print("[cursor-log] No Cursor agent-transcripts directory found.", file=sys.stderr)
        sys.exit(0)

    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "session.jsonl"
    logged_ids = get_logged_entry_ids(log_file)

    cutoff = None
    if not args.all:
        cutoff = datetime.now(tz=VN_TZ) - timedelta(hours=args.hours)

    repo = git("git remote get-url origin").split("/")[-1].replace(".git", "")
    branch = git("git rev-parse --abbrev-ref HEAD")
    commit = git("git rev-parse --short HEAD")
    student = git("git config user.email") or os.environ.get(
        "USERNAME",
        os.environ.get("USER", "unknown"),
    )

    new_entries: list[dict] = []
    for msg in iter_user_inputs(
        roots,
        cutoff,
        args.conv_id,
        repo_slug,
        args.no_repo_filter,
    ):
        entry = build_entry(msg, repo or repo_root.name, branch, commit, student)
        if entry["entry_id"] in logged_ids:
            continue
        new_entries.append(entry)
        logged_ids.add(entry["entry_id"])

    if not new_entries:
        scope = "all" if args.all else f"{args.hours}h"
        repo_note = "any repo" if args.no_repo_filter else f"repo={repo_slug}"
        print(f"[cursor-log] No new prompts ({repo_note}, window={scope}).", file=sys.stderr)
        sys.exit(0)

    if args.dry_run:
        print(f"\n[cursor-log] DRY RUN — would log {len(new_entries)} entries:\n")
        for entry in new_entries:
            preview = entry["prompt"].replace("\n", " ")[:120]
            print(f"  [{entry['entry_id']}] {preview}")
        sys.exit(0)

    with open(log_file, "a", encoding="utf-8") as f:
        for entry in new_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[cursor-log] Logged {len(new_entries)} prompt(s) from Cursor.", file=sys.stderr)


if __name__ == "__main__":
    main()

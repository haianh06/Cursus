#!/usr/bin/env python3
"""Drives git_info_host.py over the real native-messaging framing.

The installer runs this so it can say "installed" only when the host actually
answers — a registry key that points at a broken launcher looks identical to a
working one until Chrome quietly fails weeks later.

  python selftest.py [repo_path]
"""
import json
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOST = HERE / "git_info_host.py"


def call(messages, repo=None):
    """Send framed requests, return the framed replies."""
    payload = b""
    for msg in messages:
        body = json.dumps(msg).encode("utf-8")
        payload += struct.pack("@I", len(body)) + body

    proc = subprocess.run(
        [sys.executable, str(HOST)],
        input=payload,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"host exited {proc.returncode}: {proc.stderr.decode('utf-8', 'replace')}")

    out = proc.stdout
    replies = []
    pos = 0
    while pos + 4 <= len(out):
        (length,) = struct.unpack("@I", out[pos:pos + 4])
        pos += 4
        replies.append(json.loads(out[pos:pos + length].decode("utf-8")))
        pos += length
    return replies


def main() -> int:
    repo = sys.argv[1] if len(sys.argv) > 1 else None
    failures = []

    def check(name, cond, extra=""):
        if cond:
            print(f"  PASS  {name}")
        else:
            failures.append(name)
            print(f"  FAIL  {name} {extra}")

    try:
        replies = call([
            {"action": "ping"},
            {"action": "repoinfo", "repo": repo} if repo else {"action": "repoinfo"},
            {"action": "nonsense"},
        ])
    except Exception as exc:
        print(f"  FAIL  host khong chay duoc: {exc}")
        return 1

    check("host tra ve du 3 reply", len(replies) == 3, f"-> {len(replies)}")
    if len(replies) < 3:
        return 1

    ping, info, junk = replies
    check("ping ok", ping.get("ok") is True, ping)
    check("action la khong hop le bi tu choi", junk.get("ok") is False, junk)

    if not info.get("ok"):
        print(f"  FAIL  repoinfo: {info.get('error')}")
        return 1

    check("co commit", bool(info.get("commit")), info)
    check("commit dang short sha", len(info.get("commit", "")) >= 7, info.get("commit"))
    check("co branch", bool(info.get("branch")), info)
    check("dirty la bool", isinstance(info.get("dirty"), bool), info.get("dirty"))

    print("")
    print(f"  repo    : {info.get('repo') or '(khong co remote origin)'}")
    print(f"  branch  : {info.get('branch')}")
    print(f"  commit  : {info.get('commit')}  {info.get('message')}")
    print(f"  student : {info.get('student')}")
    print(f"  dirty   : {info.get('dirty')}")
    if info.get("upstream"):
        print(f"  unpushed: {info.get('unpushed')} commit chua push")
    else:
        print("  unpushed: (branch chua co upstream)")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

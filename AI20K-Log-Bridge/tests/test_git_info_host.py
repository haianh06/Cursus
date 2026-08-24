"""Native messaging host protocol and git derivation.

Runs the host as a real subprocess over the real length-prefixed framing —
mocking the transport would hide the two failures that actually bite: framing
corrupted by Windows newline translation, and a stray print on stdout.
"""
import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

def _find_host() -> Path:
    """Locate git_info_host.py without assuming a fixed repo layout.

    The extension folder is meant to be copied into other projects, so pinning
    `parents[1]/tools/ai-log-extension` would break this suite the moment it
    lands somewhere slightly different.
    """
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "tools" / "ai-log-extension" / "native" / "git_info_host.py",
        here.parent / "native" / "git_info_host.py",
        here.parents[1] / "native" / "git_info_host.py",
    ]
    for base in here.parents[:5]:
        candidates.append(base / "ai-log-extension" / "native" / "git_info_host.py")
    for c in candidates:
        if c.exists():
            return c
    raise RuntimeError("Khong tim thay git_info_host.py o gan " + str(here))


HOST = _find_host()


def frame(msg: dict) -> bytes:
    body = json.dumps(msg).encode("utf-8")
    return struct.pack("@I", len(body)) + body


def unframe(raw: bytes) -> list:
    out, pos = [], 0
    while pos + 4 <= len(raw):
        (length,) = struct.unpack("@I", raw[pos:pos + 4])
        pos += 4
        out.append(json.loads(raw[pos:pos + length].decode("utf-8")))
        pos += length
    return out


def call(*messages) -> list:
    payload = b"".join(frame(m) for m in messages)
    proc = subprocess.run([sys.executable, str(HOST)], input=payload,
                          capture_output=True, timeout=30)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    return unframe(proc.stdout)


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    """A throwaway git repo, so assertions do not depend on this checkout."""
    path = tmp_path_factory.mktemp("repo")

    def git(*args):
        return subprocess.run(["git"] + list(args), cwd=path, capture_output=True,
                              text=True, timeout=30)

    git("init", "-b", "main")
    git("config", "user.email", "sinhvien@fpt.edu.vn")
    git("config", "user.name", "Sinh Vien")
    git("remote", "add", "origin", "https://github.com/AI20K-Build-Cohort-2/P-999.git")
    (path / "a.txt").write_text("xin chao", encoding="utf-8")
    git("add", "a.txt")
    git("commit", "-m", "feat: commit dau tien")
    return path


def test_ping():
    (reply,) = call({"action": "ping"})
    assert reply["ok"] is True
    assert reply["version"]


def test_unknown_action_is_refused():
    (reply,) = call({"action": "khong-co-that"})
    assert reply["ok"] is False
    assert "unknown action" in reply["error"]


def test_several_messages_in_one_stream():
    replies = call({"action": "ping"}, {"action": "ping"}, {"action": "ping"})
    assert len(replies) == 3
    assert all(r["ok"] for r in replies)


def test_repoinfo_reads_the_working_tree(repo):
    (reply,) = call({"action": "repoinfo", "repo": str(repo)})
    assert reply["ok"] is True
    assert reply["branch"] == "main"
    assert reply["student"] == "sinhvien@fpt.edu.vn"
    # Same derivation log_hook.py uses, so both agree on the team name.
    assert reply["repo"] == "P-999"
    assert reply["message"] == "feat: commit dau tien"
    assert len(reply["commit"]) >= 7
    assert reply["full"].startswith(reply["commit"])
    assert reply["dirty"] is False


def test_repoinfo_reports_uncommitted_work(repo):
    """The one thing the GitHub API can never see."""
    (path := repo / "b.txt").write_text("chua commit", encoding="utf-8")
    try:
        (reply,) = call({"action": "repoinfo", "repo": str(repo)})
        assert reply["dirty"] is True
    finally:
        path.unlink()


def test_commit_tracks_new_commits(repo):
    (before,) = call({"action": "repoinfo", "repo": str(repo)})

    (repo / "c.txt").write_text("them file", encoding="utf-8")
    subprocess.run(["git", "add", "c.txt"], cwd=repo, capture_output=True, timeout=30)
    subprocess.run(["git", "commit", "-m", "feat: commit thu hai"], cwd=repo,
                   capture_output=True, timeout=30)

    (after,) = call({"action": "repoinfo", "repo": str(repo)})
    assert after["commit"] != before["commit"]
    assert after["message"] == "feat: commit thu hai"


def test_non_repo_path_is_rejected(tmp_path):
    """Must not silently answer with some ancestor repo's commit.

    `git rev-parse --is-inside-work-tree` walks upward, and a versioned home
    directory makes almost every path under it look like a work tree — so a
    mistyped path would otherwise report an unrelated project's commit.
    """
    (reply,) = call({"action": "repoinfo", "repo": str(tmp_path)})
    assert reply["ok"] is False
    assert "gốc" in reply["error"]


def test_explicit_bad_path_does_not_fall_back(tmp_path, repo):
    """An explicitly named repo must resolve or fail.

    Falling back to the installed default would answer about repo Y while the
    caller asked about repo X — the same wrong-commit failure in a new costume.
    Only a request that names no repo may use the configured default.
    """
    cfg_path = HOST.parent / "host_config.json"
    saved = cfg_path.read_bytes() if cfg_path.exists() else None
    cfg_path.write_text(json.dumps({"repo": str(repo)}), encoding="utf-8")
    try:
        (explicit,) = call({"action": "repoinfo", "repo": str(tmp_path)})
        assert explicit["ok"] is False, "duong dan sai phai bao loi, khong duoc roi ve mac dinh"

        (implicit,) = call({"action": "repoinfo"})
        assert implicit["ok"] is True, "khong truyen repo thi moi dung mac dinh"
        assert implicit["branch"] == "main"
    finally:
        if saved is None:
            cfg_path.unlink()
        else:
            cfg_path.write_bytes(saved)


def test_subdirectory_is_rejected(repo):
    """Same guard, stated positively: only the repo root is accepted."""
    sub = repo / "src"
    sub.mkdir(exist_ok=True)
    (reply,) = call({"action": "repoinfo", "repo": str(sub)})
    assert reply["ok"] is False


def test_missing_path_is_rejected():
    (reply,) = call({"action": "repoinfo", "repo": "/khong/ton/tai/o/dau/ca"})
    assert reply["ok"] is False


def test_branches_lists_real_refs(repo):
    """Free-text branch names let a typo pick the wrong commit silently; the
    popup offers this list instead so the name cannot be misspelled."""
    subprocess.run(["git", "branch", "feature/x"], cwd=repo, capture_output=True, timeout=30)
    try:
        (reply,) = call({"action": "branches", "repo": str(repo)})
        assert reply["ok"] is True
        assert reply["current"] == "main"
        names = {b["name"] for b in reply["branches"]}
        assert names == {"main", "feature/x"}
        by_name = {b["name"]: b for b in reply["branches"]}
        assert by_name["main"]["current"] is True
        assert by_name["feature/x"]["current"] is False
        assert len(by_name["main"]["commit"]) >= 7
    finally:
        subprocess.run(["git", "branch", "-D", "feature/x"], cwd=repo,
                       capture_output=True, timeout=30)


def test_pinned_branch_reports_that_branch(repo):
    """A pinned branch is read even when it is not the one checked out."""
    subprocess.run(["git", "branch", "other"], cwd=repo, capture_output=True, timeout=30)
    (repo / "d.txt").write_text("chi tren main", encoding="utf-8")
    subprocess.run(["git", "add", "d.txt"], cwd=repo, capture_output=True, timeout=30)
    subprocess.run(["git", "commit", "-m", "feat: chi tren main"], cwd=repo,
                   capture_output=True, timeout=30)
    try:
        (head,) = call({"action": "repoinfo", "repo": str(repo)})
        (other,) = call({"action": "repoinfo", "repo": str(repo), "branch": "other"})

        assert head["branch"] == "main"
        assert head["pinned"] is False
        assert other["ok"] is True
        assert other["branch"] == "other"
        assert other["pinned"] is True
        assert other["current_branch"] == "main"
        # `other` was cut before the newest commit, so the two must differ.
        assert other["commit"] != head["commit"]
        assert other["message"] == "feat: commit thu hai"
    finally:
        subprocess.run(["git", "branch", "-D", "other"], cwd=repo,
                       capture_output=True, timeout=30)


def test_unknown_branch_is_rejected(repo):
    """Loudly — the whole point is not to stamp entries with a wrong commit."""
    (reply,) = call({"action": "repoinfo", "repo": str(repo), "branch": "khong-co-that"})
    assert reply["ok"] is False
    assert "khong-co-that" in reply["error"]


def test_config_with_utf8_bom_is_read(repo, monkeypatch):
    """PowerShell's `Set-Content -Encoding utf8` writes a BOM.

    Reading that back as plain utf-8 makes json.loads fail on the first
    character, and the host then behaves exactly as if it had never been
    configured — the popup says "chưa cài native host" while everything looks
    installed. Regression guard: the real installer hit this.
    """
    cfg_path = HOST.parent / "host_config.json"
    saved = cfg_path.read_bytes() if cfg_path.exists() else None
    body = json.dumps({"repo": str(repo), "debug": False}, ensure_ascii=False)
    cfg_path.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))
    try:
        # No explicit repo, so the host must fall back to the BOM'd config.
        (reply,) = call({"action": "repoinfo"})
        assert reply["ok"] is True, reply.get("error")
        assert reply["branch"] == "main"
    finally:
        if saved is None:
            cfg_path.unlink()
        else:
            cfg_path.write_bytes(saved)


def test_stdout_carries_only_framed_replies(repo):
    """A stray print would desync every later message on the stream."""
    payload = frame({"action": "ping"}) + frame({"action": "repoinfo", "repo": str(repo)})
    proc = subprocess.run([sys.executable, str(HOST)], input=payload,
                          capture_output=True, timeout=30)
    raw = proc.stdout
    pos = 0
    seen = 0
    while pos + 4 <= len(raw):
        (length,) = struct.unpack("@I", raw[pos:pos + 4])
        pos += 4 + length
        seen += 1
    assert seen == 2
    assert pos == len(raw), "co byte thua tren stdout ngoai cac reply"


def test_truncated_frame_does_not_hang():
    """A half-written length prefix must end the loop, not block forever."""
    proc = subprocess.run([sys.executable, str(HOST)], input=b"\x02\x00",
                          capture_output=True, timeout=30)
    assert proc.returncode == 0
    assert proc.stdout == b""


def test_oversized_length_is_refused():
    """Guards against a bogus prefix making the host allocate wildly."""
    proc = subprocess.run([sys.executable, str(HOST)],
                          input=struct.pack("@I", 50 * 1024 * 1024) + b"{}",
                          capture_output=True, timeout=30)
    assert proc.returncode == 0
    assert proc.stdout == b""

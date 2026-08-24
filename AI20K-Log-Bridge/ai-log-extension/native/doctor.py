#!/usr/bin/env python3
"""Kiểm tra toàn bộ cài đặt AI Log Bridge — chạy sau khi cấu hình xong.

    python tools/ai-log-extension/native/doctor.py

Mỗi mục hỏng đều kèm cách sửa. Thà nói thẳng "hỏng ở bước 4, làm thế này" còn
hơn để người dùng thấy extension im lặng rồi tự đoán.

Thêm --server để thử gọi grading server luôn (gửi batch rỗng, không ghi gì).
"""
import argparse
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXT_DIR = HERE.parent
REPO_ROOT = EXT_DIR.parent.parent

HOST_NAME = "com.ai20k.gitinfo"
EXTENSION_ID = "cheofncpckkpmfjoeflampnmainmblac"

# Mọi hướng dẫn sửa lỗi đều trỏ về đây, để đổi tên lệnh chỉ phải sửa một chỗ —
# một script chỉ dẫn người dùng chạy lệnh không còn tồn tại là ngõ cụt.
SETUP = r"tools\ai-log-extension\setup.cmd"
SETUP_SH = "bash tools/ai-log-extension/setup.sh"

OK, WARN, FAIL = "OK", "WARN", "FAIL"
ICON = {OK: "[ OK ]", WARN: "[WARN]", FAIL: "[FAIL]"}

results = []


def add(status, title, detail="", fix=""):
    results.append((status, title, detail, fix))
    return status


def section(name):
    print(f"\n{name}")
    print("-" * len(name))


def show(status, title, detail="", fix=""):
    print(f"  {ICON[status]} {title}")
    if detail:
        print(f"         {detail}")
    if fix and status != OK:
        for line in fix.splitlines():
            print(f"         -> {line}")
    add(status, title, detail, fix)


# --------------------------------------------------------------------------
# 1. Môi trường
# --------------------------------------------------------------------------

def check_python():
    v = sys.version_info
    if v < (3, 8):
        return show(FAIL, "Python", f"{v.major}.{v.minor}", "Cần Python 3.8 trở lên.")
    show(OK, "Python", f"{v.major}.{v.minor}.{v.micro} — {sys.executable}")


def check_git():
    try:
        out = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=15)
        if out.returncode == 0:
            return show(OK, "git", out.stdout.strip())
    except Exception:
        pass
    show(FAIL, "git", "không gọi được",
         "Cài Git và đảm bảo `git` nằm trong PATH.")


# --------------------------------------------------------------------------
# 2. Native host
# --------------------------------------------------------------------------

def read_host_config():
    p = HERE / "host_config.json"
    if not p.exists():
        show(FAIL, "host_config.json", "chưa có",
             "Chưa cài. Chạy một lệnh:\n"
             f"{SETUP}   (macOS/Linux: {SETUP_SH})")
        return None
    try:
        # utf-8-sig tolerates the BOM that PowerShell's Set-Content writes.
        cfg = json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        show(FAIL, "host_config.json", f"không đọc được: {exc}",
             "Chạy lại: tools\\ai-log-extension\\setup.cmd")
        return None
    show(OK, "host_config.json", f"repo = {cfg.get('repo')}")
    return cfg


def check_repo_path(cfg):
    if not cfg:
        return None
    path = Path(str(cfg.get("repo", ""))).expanduser()
    if not path.is_dir():
        show(FAIL, "Đường dẫn repo", f"{path} không tồn tại",
             "Chạy lại với đường dẫn đúng:\n"
             f"{SETUP} --repo \"D:\\duong\\dan\\repo\"")
        return None

    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path,
                             capture_output=True, text=True, timeout=15)
        toplevel = top.stdout.strip() if top.returncode == 0 else ""
    except Exception:
        toplevel = ""

    if not toplevel:
        show(FAIL, "Đường dẫn repo", f"{path} không phải git repo",
             "Trỏ vào thư mục chứa .git.")
        return None

    if Path(toplevel).resolve() != path.resolve():
        # Điểm này quan trọng: git dò ngược lên cây thư mục, nên trỏ vào thư mục
        # con (hay nhầm sang thư mục home đang là repo) sẽ báo commit của repo khác.
        show(FAIL, "Đường dẫn repo", f"{path} nằm TRONG repo {toplevel}, không phải gốc",
             "Host chỉ nhận đúng gốc repo, để tránh báo nhầm commit của project khác.\n"
             f"Chạy lại: tools\\ai-log-extension\\setup.cmd --repo \"{toplevel}\"")
        return None

    show(OK, "Đường dẫn repo", str(path))
    return path


def call_host(messages):
    payload = b""
    for m in messages:
        body = json.dumps(m).encode("utf-8")
        payload += struct.pack("@I", len(body)) + body
    proc = subprocess.run([sys.executable, str(HERE / "git_info_host.py")],
                          input=payload, capture_output=True, timeout=30)
    out, pos, replies = proc.stdout, 0, []
    while pos + 4 <= len(out):
        (n,) = struct.unpack("@I", out[pos:pos + 4])
        pos += 4
        replies.append(json.loads(out[pos:pos + n].decode("utf-8")))
        pos += n
    return replies, proc


def check_host_runs():
    if not (HERE / "git_info_host.py").exists():
        return show(FAIL, "git_info_host.py", "không có file",
                    "Kéo lại repo — thiếu file trong tools/ai-log-extension/native/.")
    try:
        replies, proc = call_host([{"action": "ping"}, {"action": "repoinfo"}])
    except Exception as exc:
        return show(FAIL, "Host chạy thử", str(exc), "Xem host.log sau khi bật debug.")

    if len(replies) < 2:
        return show(FAIL, "Host chạy thử", "không trả lời đủ",
                    proc.stderr.decode("utf-8", "replace")[:300] or "Không rõ lý do.")

    ping, info = replies[0], replies[1]
    if not ping.get("ok"):
        return show(FAIL, "Host trả lời ping", str(ping))
    show(OK, "Host trả lời ping", f"version {ping.get('version')}")

    if not info.get("ok"):
        return show(FAIL, "Host đọc git", info.get("error", ""),
                    f"Chạy lại: {SETUP} --repo \"<gốc repo>\"")
    show(OK, "Host đọc git",
         f"repo={info.get('repo') or '(không có origin)'} · "
         f"branch={info.get('branch')} · commit={info.get('commit')}")
    return info


def check_launcher():
    name = "run_host.bat" if sys.platform == "win32" else "run_host.sh"
    p = HERE / name
    if not p.exists():
        return show(FAIL, name, "chưa có", f"Chạy: {SETUP}")
    show(OK, name, str(p))
    return p


def check_native_manifest(launcher):
    p = HERE / f"{HOST_NAME}.json"
    if not p.exists():
        return show(FAIL, "Manifest native host", "chưa có", f"Chạy: {SETUP}")
    try:
        m = json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return show(FAIL, "Manifest native host", f"không đọc được: {exc}")

    problems = []
    if m.get("name") != HOST_NAME:
        problems.append(f"name = {m.get('name')!r}, phải là {HOST_NAME!r}")
    if launcher and Path(str(m.get("path", ""))).resolve() != Path(launcher).resolve():
        problems.append(f"path trỏ sai: {m.get('path')}")
    origins = m.get("allowed_origins") or []
    want = f"chrome-extension://{EXTENSION_ID}/"
    if want not in origins:
        problems.append(f"allowed_origins thiếu {want}")

    if problems:
        return show(FAIL, "Manifest native host", "; ".join(problems),
                    f"Chạy lại {SETUP} để ghi đè file này.")
    show(OK, "Manifest native host", str(p))
    return p


def check_registration(manifest_path):
    if sys.platform == "win32":
        import winreg
        roots = [
            ("Chrome", r"Software\Google\Chrome\NativeMessagingHosts"),
            ("Edge", r"Software\Microsoft\Edge\NativeMessagingHosts"),
        ]
        found = 0
        for label, sub in roots:
            key_path = sub + "\\" + HOST_NAME
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as k:
                    value, _ = winreg.QueryValueEx(k, "")
            except FileNotFoundError:
                show(WARN, f"Đăng ký với {label}", "chưa có khoá registry",
                     f"Bỏ qua nếu bạn không dùng {label}. Nếu có dùng thì chạy lại {SETUP}.")
                continue
            except Exception as exc:
                show(WARN, f"Đăng ký với {label}", str(exc))
                continue

            if manifest_path and Path(value).resolve() != Path(manifest_path).resolve():
                show(FAIL, f"Đăng ký với {label}", f"trỏ sai: {value}",
                     f"Chạy lại {SETUP}.")
            else:
                show(OK, f"Đăng ký với {label}", value)
                found += 1
        if not found:
            show(FAIL, "Đăng ký trình duyệt", "không trình duyệt nào được đăng ký",
                 f"Chạy {SETUP}, rồi KHỞI ĐỘNG LẠI trình duyệt.")
        return

    home = Path.home()
    if sys.platform == "darwin":
        dirs = {
            "Chrome": home / "Library/Application Support/Google/Chrome/NativeMessagingHosts",
            "Edge": home / "Library/Application Support/Microsoft Edge/NativeMessagingHosts",
        }
    else:
        dirs = {
            "Chrome": home / ".config/google-chrome/NativeMessagingHosts",
            "Edge": home / ".config/microsoft-edge/NativeMessagingHosts",
        }
    found = 0
    for label, d in dirs.items():
        f = d / f"{HOST_NAME}.json"
        if f.exists():
            show(OK, f"Đăng ký với {label}", str(f))
            found += 1
        else:
            show(WARN, f"Đăng ký với {label}", "chưa có", f"Bỏ qua nếu không dùng {label}.")
    if not found:
        show(FAIL, "Đăng ký trình duyệt", "không trình duyệt nào được đăng ký",
             "Chạy: bash ai-log-extension/setup.sh, rồi khởi động lại trình duyệt.")


# --------------------------------------------------------------------------
# 3. Extension
# --------------------------------------------------------------------------

def check_extension_manifest():
    p = EXT_DIR / "manifest.json"
    if not p.exists():
        return show(FAIL, "manifest.json của extension", "không có file")
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return show(FAIL, "manifest.json của extension", f"JSON hỏng: {exc}")

    if not m.get("key"):
        return show(FAIL, "Extension ID ghim", "thiếu trường key",
                    "Thiếu key thì Chrome tự sinh ID theo đường dẫn, và native host\n"
                    "sẽ từ chối vì allowed_origins không khớp.")
    show(OK, "Extension ID ghim", EXTENSION_ID)

    if "nativeMessaging" not in (m.get("permissions") or []):
        show(FAIL, "Quyền nativeMessaging", "thiếu trong manifest",
             "Thiếu quyền này thì extension không gọi được host.")
    else:
        show(OK, "Quyền nativeMessaging", "có")


# --------------------------------------------------------------------------
# 4. Grading server
# --------------------------------------------------------------------------

def check_env_and_server(test_server):
    env = REPO_ROOT / ".env"
    if not env.exists():
        return show(WARN, "File .env", "không thấy",
                    "Cần AI_LOG_SERVER và AI_LOG_API_KEY để điền vào popup.")
    values = {}
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip()

    server = values.get("AI_LOG_SERVER", "")
    key = values.get("AI_LOG_API_KEY", "")
    if not server or not key:
        return show(FAIL, "Cấu hình trong .env",
                    f"AI_LOG_SERVER={'có' if server else 'thiếu'}, "
                    f"AI_LOG_API_KEY={'có' if key else 'thiếu'}",
                    "Hỏi BTC hai giá trị này.")
    show(OK, "Cấu hình trong .env", server)

    if not test_server:
        show(WARN, "Gọi thử server", "bỏ qua", "Thêm --server để thử gọi thật.")
        return

    import urllib.error
    import urllib.request
    req = urllib.request.Request(
        server, data=b'{"entries":[]}', method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            show(OK, "Gọi thử server", f"HTTP {resp.status} (gửi batch rỗng, không ghi gì)")
    except urllib.error.HTTPError as exc:
        show(FAIL, "Gọi thử server", f"HTTP {exc.code}",
             "401/403 = API key sai. 404 = URL sai. Hỏi lại BTC.")
    except Exception as exc:
        show(FAIL, "Gọi thử server", str(exc), "Kiểm tra mạng hoặc URL.")


# --------------------------------------------------------------------------

def run_checks(test_server: bool = False) -> int:
    """Chạy toàn bộ kiểm tra, in báo cáo, trả 0 nếu không mục nào FAIL.

    Tách khỏi main() để setup.py gọi lại ngay sau khi cài — cài xong mà không
    kiểm tra ngay là cách chắc chắn nhất để một cấu hình hỏng nằm im hàng tuần.
    """
    results.clear()

    section("1. Moi truong")
    check_python()
    check_git()

    section("2. Native host (de lay commit that tren may)")
    cfg = read_host_config()
    check_repo_path(cfg)
    check_host_runs()
    launcher = check_launcher()
    manifest = check_native_manifest(launcher)
    check_registration(manifest)

    section("3. Extension")
    check_extension_manifest()

    section("4. Grading server")
    check_env_and_server(test_server)

    fails = [r for r in results if r[0] == FAIL]
    warns = [r for r in results if r[0] == WARN]

    print("\n" + "=" * 62)
    if not fails:
        print(f" TAT CA DAT ({len(results) - len(warns)} muc OK"
              + (f", {len(warns)} canh bao" if warns else "") + ")")
        print("=" * 62)
        return 0

    print(f" CON {len(fails)} MUC HONG")
    print("=" * 62)
    for i, (_, title, detail, fix) in enumerate(fails, 1):
        print(f"\n{i}. {title}" + (f" — {detail}" if detail else ""))
        for line in (fix or "").splitlines():
            print(f"   {line}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Kiểm tra cài đặt AI Log Bridge")
    ap.add_argument("--server", action="store_true", help="gọi thử grading server")
    args = ap.parse_args()

    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("=" * 62)
    print(" KIEM TRA CAI DAT — AI20K Log Bridge")
    print("=" * 62)
    return run_checks(args.server)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Cài đặt VÀ kiểm tra AI Log Bridge — một lệnh duy nhất.

    tools\\ai-log-extension\\setup.cmd          (Windows)
    bash tools/ai-log-extension/setup.sh       (macOS / Linux)

Chạy lại bao nhiêu lần cũng được — nó ghi đè bằng giá trị đúng, không nhân bản.

Tuỳ chọn:
    --check         chỉ kiểm tra, không ghi gì
    --repo PATH     trỏ vào repo khác (mặc định: repo chứa script này)
    --server        gọi thử grading server (gửi batch rỗng, không ghi log nào)
    --uninstall     gỡ đăng ký native host

Trước đây việc này cần 4 lệnh khác nhau cho Windows và macOS/Linux, cài và kiểm
tra tách rời. Cài xong mà không kiểm tra ngay là cách chắc chắn nhất để một khoá
registry hỏng nằm im vài tuần.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NATIVE = HERE / "native"
REPO_ROOT = HERE.parent.parent

sys.path.insert(0, str(NATIVE))
import doctor  # noqa: E402  (đường dẫn phải được thêm trước)

HOST_NAME = doctor.HOST_NAME
EXTENSION_ID = doctor.EXTENSION_ID


def out(msg=""):
    print(msg)


def find_python(repo: Path) -> str:
    """Ưu tiên venv của repo — host cần chạy được kể cả khi PATH bị rút gọn."""
    for cand in (repo / ".venv/Scripts/python.exe", repo / ".venv/bin/python"):
        if cand.exists():
            return str(cand)
    return sys.executable


def resolve_repo(explicit) -> Path | None:
    """Chỉ nhận gốc repo. git dò ngược lên cây thư mục, nên một đường dẫn sai
    vẫn có thể 'nằm trong' repo nào đó và cho ra commit của project khác."""
    path = Path(explicit).expanduser().resolve() if explicit else REPO_ROOT
    if not path.is_dir():
        return None
    try:
        res = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path,
                             capture_output=True, text=True, timeout=15)
    except Exception:
        return None
    if res.returncode != 0:
        return None
    top = Path(res.stdout.strip()).resolve()
    return path if top == path else top


# --------------------------------------------------------------------------
# Cài đặt
# --------------------------------------------------------------------------

def write_launcher(python_exe: str) -> Path:
    if sys.platform == "win32":
        p = NATIVE / "run_host.bat"
        p.write_text(f'@echo off\r\n"{python_exe}" "{NATIVE / "git_info_host.py"}" %*\r\n',
                     encoding="utf-8")
    else:
        p = NATIVE / "run_host.sh"
        p.write_text(f'#!/usr/bin/env bash\nexec "{python_exe}" "{NATIVE / "git_info_host.py"}" "$@"\n',
                     encoding="utf-8")
        p.chmod(0o755)
    return p


def write_host_config(repo: Path, debug: bool) -> Path:
    p = NATIVE / "host_config.json"
    p.write_text(json.dumps({"repo": str(repo), "debug": debug}, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    return p


def write_native_manifest(launcher: Path) -> Path:
    p = NATIVE / f"{HOST_NAME}.json"
    p.write_text(json.dumps({
        "name": HOST_NAME,
        "description": "AI20K git info for the AI Log Bridge extension",
        "path": str(launcher),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{EXTENSION_ID}/"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def browser_targets():
    """(nhãn, nơi đăng ký) cho từng trình duyệt trên nền tảng hiện tại."""
    if sys.platform == "win32":
        return [("Chrome", r"Software\Google\Chrome\NativeMessagingHosts"),
                ("Edge", r"Software\Microsoft\Edge\NativeMessagingHosts")]
    home = Path.home()
    if sys.platform == "darwin":
        base = home / "Library/Application Support"
        return [("Chrome", base / "Google/Chrome/NativeMessagingHosts"),
                ("Edge", base / "Microsoft Edge/NativeMessagingHosts"),
                ("Chromium", base / "Chromium/NativeMessagingHosts")]
    return [("Chrome", home / ".config/google-chrome/NativeMessagingHosts"),
            ("Edge", home / ".config/microsoft-edge/NativeMessagingHosts"),
            ("Chromium", home / ".config/chromium/NativeMessagingHosts")]


def register(manifest: Path) -> int:
    done = 0
    if sys.platform == "win32":
        import winreg
        for label, sub in browser_targets():
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub + "\\" + HOST_NAME) as k:
                    winreg.SetValueEx(k, "", 0, winreg.REG_SZ, str(manifest))
                out(f"  dang ky {label}: HKCU\\{sub}\\{HOST_NAME}")
                done += 1
            except Exception as exc:
                out(f"  KHONG dang ky duoc {label}: {exc}")
        return done

    for label, d in browser_targets():
        # Chỉ ghi cho trình duyệt thực sự có mặt — tạo cả cây thư mục cho một
        # trình duyệt chưa cài chỉ để lại rác.
        if not d.parent.exists():
            continue
        try:
            d.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(manifest, d / f"{HOST_NAME}.json")
            out(f"  dang ky {label}: {d / f'{HOST_NAME}.json'}")
            done += 1
        except Exception as exc:
            out(f"  KHONG dang ky duoc {label}: {exc}")
    return done


def unregister() -> int:
    done = 0
    if sys.platform == "win32":
        import winreg
        for label, sub in browser_targets():
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub + "\\" + HOST_NAME)
                out(f"  da go {label}")
                done += 1
            except FileNotFoundError:
                pass
            except Exception as exc:
                out(f"  khong go duoc {label}: {exc}")
        return done

    for label, d in browser_targets():
        f = d / f"{HOST_NAME}.json"
        if f.exists():
            try:
                f.unlink()
                out(f"  da go {label}")
                done += 1
            except Exception as exc:
                out(f"  khong go duoc {label}: {exc}")
    return done


def install(repo: Path, debug: bool) -> bool:
    python_exe = find_python(repo)
    out(f"  python  : {python_exe}")
    out(f"  repo    : {repo}")

    launcher = write_launcher(python_exe)
    out(f"  launcher: {launcher.name}")
    write_host_config(repo, debug)
    manifest = write_native_manifest(launcher)
    out(f"  manifest: {manifest.name}")

    n = register(manifest)
    if n == 0:
        out("  KHONG trinh duyet nao duoc dang ky.")
        return False
    return True


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Cai dat va kiem tra AI Log Bridge")
    ap.add_argument("--check", action="store_true", help="chi kiem tra, khong ghi gi")
    ap.add_argument("--repo", default="", help="duong dan goc repo")
    ap.add_argument("--server", action="store_true", help="goi thu grading server")
    ap.add_argument("--debug", action="store_true", help="bat host.log")
    ap.add_argument("--uninstall", action="store_true", help="go dang ky native host")
    args = ap.parse_args()

    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    out("=" * 62)
    out(" AI20K Log Bridge — cai dat & kiem tra")
    out("=" * 62)

    if args.uninstall:
        out("\nGo dang ky native host")
        out("-" * 22)
        n = unregister()
        out(f"\nDa go {n} dang ky. Khoi dong lai trinh duyet de co hieu luc.")
        return 0

    if not shutil.which("git"):
        out("\n[FAIL] Khong tim thay git. Cai Git roi chay lai.")
        return 1

    if not args.check:
        repo = resolve_repo(args.repo)
        if repo is None:
            target = args.repo or str(REPO_ROOT)
            out(f"\n[FAIL] '{target}' khong phai goc mot git repo.")
            out("       Chay lai voi: --repo \"D:\\duong\\dan\\repo\"")
            return 1

        out("\nCai dat")
        out("-" * 7)
        if not install(repo, args.debug):
            out("\n[FAIL] Cai dat khong hoan tat — xem thong bao o tren.")
            return 1

    rc = doctor.run_checks(args.server)

    if rc == 0:
        out("\nBuoc tiep theo:")
        out("  1. chrome://extensions -> Load unpacked -> chon tools/ai-log-extension")
        out(f"     (kiem tra ID phai la {EXTENSION_ID})")
        out("  2. KHOI DONG LAI trinh duyet — Chrome chi doc dang ky luc khoi dong")
        out("  3. Mo popup -> muc 'Bat dau' -> bam 'Kiem tra tat ca'")
    return rc


if __name__ == "__main__":
    sys.exit(main())

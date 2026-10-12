#!/usr/bin/env python3
"""
Leftover's  v1.8.0
Windows only. Notepad++: Encoding UTF-8, then run with Python 3.

Scans selected local drives, including Program Files and Program Files (x86).
Link AI checks Ollama, starts it, and lets you pick the local agent.
The agent only nominates leftovers. The app double-checks every path
and refuses Windows, OEM, Nahimic, installed apps, and anything still in use.
Dry-run is on until you turn it off.
"""

import os
import sys
import json
import ctypes
import logging
import tempfile
import threading
import traceback
import subprocess
import shutil
import urllib.request
from pathlib import Path
from datetime import datetime

APP_NAME = "Leftover's"
VERSION = "0.8.0"

if sys.platform != "win32":
    print("This script only runs on Windows.")
    try:
        input("Press Enter to exit...")
    except Exception:
        pass
    sys.exit(1)

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

PS = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
CREATE_NO_WINDOW = 0x08000000
DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3
MIN_SIZE = 50 * 1024
OLLAMA = "http://127.0.0.1:11434"

SKIP_TOP = {
    "windows", "users", "$recycle.bin", "system volume information", "recovery",
    "documents and settings", "perflogs", "config.msi", "system.sav",
    "program files", "program files (x86)", "programdata",
}
SKIP_USER = {
    "public", "default", "default user", "all users", "defaultapppool",
}
PERSONAL_NAMES = {
    "documents", "my documents", "pictures", "my pictures", "videos", "my videos",
    "music", "my music", "desktop", "downloads", "favorites", "contacts",
    "saved games", "links", "onedrive", "creative cloud files",
}
MEDIA_EXT = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".heic", ".raw", ".cr2",
    ".mp4", ".mkv", ".avi", ".mov", ".mp3", ".wav", ".flac",
    ".doc", ".docx", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx", ".txt",
}
BLOCK_EXACT = {
    "windows", "windowsapps", "modifiablewindowsapps", "common files",
    "internet explorer", "windows defender", "windows nt", "windows mail",
    "reference assemblies", "msbuild", "dotnet", "microsoft",
    "microsoft office", "microsoft shared",
    "nvidia corporation", "nvidia", "intel", "amd", "realtek",
    "nahimic", "nahimic3", "avolute",
    "windows photo viewer", "windows security", "windowspowershell",
}
BLOCK_PREFIXES = (
    "microsoft.net", "windows", "nvidia", "intel", "amd", "realtek",
    "nahimic", "avolute", "dotnet",
)

DARK = {"bg": "#1b1b1b", "fg": "#e6e6e6", "field": "#2a2a2a", "button": "#3a3a3a", "select": "#0a84ff", "ok": "#7dcea0", "warn": "#e0a100"}

def app_folder():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    try:
        return Path(__file__).resolve().parent
    except Exception:
        return Path.cwd()


APP_DIR = app_folder()
LOG_DIR = APP_DIR / "logs"
try:
    LOG_DIR.mkdir(exist_ok=True)
except Exception:
    LOG_DIR = Path.cwd()
    LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"drive_scan_{datetime.now():%Y%m%d_%H%M%S}.log"
DELETED_LOG = LOG_DIR / "deleted.jsonl"
LINK_FILE = APP_DIR / "ai_link.json"
AGENT_LOG = APP_DIR / "agent_live.log"
STATE_FILE = APP_DIR / "scan_state.json"
_agent_lock = threading.Lock()
_agent_window_started = False

AI_GUIDELINES = """You are the local leftover agent for this Windows PC. You do not delete files. You only nominate folders. The application double-checks every path and will reject you if you are wrong.
NEVER nominate any of these:
- Windows itself: System32, SysWOW64, WinSxS, SystemApps, drivers, boot, recovery, servicing
- Microsoft Edge, Microsoft Store, Defender, .NET, Visual C++ runtimes, WindowsApps
- OEM and hardware folders: NVIDIA, Intel, AMD, Realtek, Dell, HP, Lenovo, ASUS, MSI, Acer, Gigabyte
- Nahimic or A-Volute, any name that contains those words
- A folder that belongs to an installed app, or that another installed app still needs
- A folder with a running process, a Windows service, or a launcher another app still uses
- Documents, pictures, music, video, or desktop files
ONLY nominate leftover app data, cache, temp, logs, or an uninstalled program that has no launcher still in use.
A standalone .exe or .lnk means the program can still run. Do not nominate that folder.
Do not nominate a folder just because it sits in Program Files.
Reply with JSON only: {"leftovers":[{"path":"exact path from the list","confidence":0.5,"reason":"why it is leftover and safe"}]}
If none qualify, return {"leftovers":[]}."""

SYS_PARTS = (
    "\\windows\\system32\\",
    "\\windows\\syswow64\\",
    "\\windows\\winsxs\\",
    "\\windows\\systemapps\\",
    "\\windows\\servicing\\",
    "\\windows\\boot\\",
    "\\windows\\fonts\\",
    "\\windows\\inf\\",
    "\\windows\\system32\\driverstore\\",
)
OEM_FOLDERS = {
    "nvidia", "nvidia corporation", "intel", "amd", "realtek", "nahimic", "nahimic3",
    "avolute", "dell", "hp", "hewlett packard", "lenovo", "asus", "msi", "acer",
    "gigabyte", "asrock", "windows defender", "microsoft edge",
}
UNINSTALLER_NAMES = {
    "unins000.exe", "uninstall.exe", "uninst.exe", "uninstaller.exe",
    "setup.exe", "unins001.exe",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("drivescan")


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    if getattr(sys, "frozen", False):
        target = sys.executable
        params = ""
    else:
        target = sys.executable
        params = f'"{Path(__file__).resolve()}"'
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", target, params, None, 1)
    return int(rc) > 32


def list_drives():
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    out = []
    for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        if not (mask & (1 << i)):
            continue
        root = f"{letter}:\\"
        kind = int(ctypes.windll.kernel32.GetDriveTypeW(root))
        if kind not in (DRIVE_FIXED, DRIVE_REMOVABLE):
            continue
        out.append((root, "USB" if kind == DRIVE_REMOVABLE else "Disk"))
    return out


def run_powershell(body, timeout=180):
    fd, name = tempfile.mkstemp(suffix=".ps1", prefix="drivescan_")
    os.close(fd)
    path = Path(name)
    path.write_text(body, encoding="utf-8-sig")
    try:
        proc = subprocess.run(
            [PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path)],
            capture_output=True, text=True, timeout=timeout, creationflags=CREATE_NO_WINDOW,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def ps_json(body, timeout=180):
    code, out, err = run_powershell(body, timeout=timeout)
    raw = (out or "").strip()
    if not raw:
        return [], err
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [], err or raw[:500]
    if isinstance(data, dict):
        data = [data]
    return data, err


APPS_PS = r"""
$ErrorActionPreference = 'Continue'
$rows = @()
$keys = @(
  'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
foreach ($k in $keys) {
  foreach ($item in (Get-ItemProperty $k -ErrorAction SilentlyContinue)) {
    $name = [string]$item.DisplayName
    if (-not $name) { continue }
    $rows += [PSCustomObject]@{
      Name = $name
      Location = ([string]$item.InstallLocation).TrimEnd('\')
      Publisher = [string]$item.Publisher
    }
  }
}
$rows | ConvertTo-Json -Compress -Depth 3
"""

RUNTIME_PS = r"""
$ErrorActionPreference = 'Continue'
$procs = @()
foreach ($p in (Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)) {
  if ($p.ExecutablePath) { $procs += [string]$p.ExecutablePath }
}
$svcs = @()
foreach ($s in (Get-CimInstance Win32_Service -ErrorAction SilentlyContinue)) {
  $m = [regex]::Match([string]$s.PathName, '"([^"]+\.exe)"|([A-Za-z]:\\[^\s]+\.exe)')
  if ($m.Success) {
    if ($m.Groups[1].Value) { $svcs += $m.Groups[1].Value } else { $svcs += $m.Groups[2].Value }
  }
}
[PSCustomObject]@{ Processes = @($procs); Services = @($svcs) } | ConvertTo-Json -Compress -Depth 4
"""

RECYCLE_PS = r"""
$ErrorActionPreference = 'Continue'
$shell = New-Object -ComObject Shell.Application
$rb = $shell.NameSpace(10)
$rows = @()
foreach ($item in @($rb.Items())) {
  $rows += [PSCustomObject]@{
    Name = [string]$item.Name
    Folder = [bool]$item.IsFolder
    Size = [int64]$item.Size
    Deleted = [string]$item.ExtendedProperty('System.Recycle.DateDeleted')
    From = [string]$item.ExtendedProperty('System.Recycle.DeletedFrom')
  }
}
$rows | ConvertTo-Json -Compress -Depth 3
"""


def find_uninstallers(folder, depth=1):
    found = []
    try:
        for child in Path(folder).iterdir():
            if child.is_file() and child.name.lower() in UNINSTALLER_NAMES:
                found.append(str(child))
            elif child.is_dir() and depth > 0:
                found.extend(find_uninstallers(child, depth - 1))
    except OSError:
        pass
    return found


def launch_uninstaller(cmd, dry_run=False):
    cmd = (cmd or "").strip()
    if not cmd:
        return False, "No uninstall command"
    if dry_run:
        return True, "[DRY-RUN] Would launch uninstaller:\n" + cmd
    try:
        subprocess.Popen(cmd, shell=True)
        return True, "Launched uninstaller:\n" + cmd
    except Exception as exc:
        return False, "Failed to launch uninstaller: " + str(exc)


def normalize(name):
    text = (name or "").lower()
    out = []
    for ch in text:
        out.append(ch if ch.isalnum() else " ")
    return " ".join("".join(out).split())


def human_size(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def is_nahimic(path):
    blob = str(path).lower().replace("-", "").replace("_", "").replace(" ", "")
    return "nahimic" in blob or "avolute" in blob


def is_blocked_name(name):
    key = normalize(name)
    if not key:
        return False
    if key in BLOCK_EXACT or is_nahimic(name):
        return True
    first = key.split()[0]
    return any(key.startswith(p) or first == p for p in BLOCK_PREFIXES)


def under(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def specific_installs(apps):
    broad = {
        "program files", "program files (x86)", "programdata", "windows",
        "users", "appdata", "local", "roaming", "locallow",
    }
    roots = []
    for app in apps:
        loc = app.get("location") or ""
        if not loc:
            continue
        folder = Path(loc)
        try:
            if not folder.exists() or len(folder.parts) <= 1:
                continue
        except OSError:
            continue
        if folder.name.lower() in broad:
            continue
        roots.append(folder)
    return roots


def installed_owns(folder, roots):
    for loc in roots:
        if under(folder, loc) or under(loc, folder):
            return True
    return False


def used_by(folder, paths):
    folder_s = str(folder).lower().rstrip("\\")
    for raw in paths:
        p = (raw or "").lower().rstrip("\\")
        if p == folder_s or p.startswith(folder_s + "\\"):
            return True
    return False


def folder_size(path, cap=2000):
    total = 0
    seen = 0
    stack = [str(path)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for ent in it:
                    seen += 1
                    if seen > cap:
                        return total
                    try:
                        if ent.is_symlink():
                            continue
                        if ent.is_file(follow_symlinks=False):
                            total += ent.stat(follow_symlinks=False).st_size
                        elif ent.is_dir(follow_symlinks=False):
                            stack.append(ent.path)
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def first_app_exe(path, depth=1, limit=40):
    """Return the program exe or shortcut that stops this folder. Uninstallers do not count."""
    try:
        with os.scandir(path) as it:
            n = 0
            for ent in it:
                n += 1
                if n > limit:
                    break
                try:
                    name = ent.name.lower()
                    if ent.is_file(follow_symlinks=False):
                        if name in UNINSTALLER_NAMES:
                            continue
                        if name.endswith(".exe") or name.endswith(".lnk"):
                            return ent.name
                    elif depth > 0 and ent.is_dir(follow_symlinks=False) and not ent.is_symlink():
                        found = first_app_exe(ent.path, 0, limit)
                        if found:
                            return found
                except OSError:
                    continue
    except OSError:
        return ""
    return ""


def has_app_launcher(path, depth=1, limit=40):
    """True when a real program launcher is here. Uninstaller stubs do not count."""
    return bool(first_app_exe(path, depth, limit))


def load_scan_state():
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_scan_state(found_count):
    data = load_scan_state()
    data["last_scan"] = datetime.now().isoformat(timespec="seconds")
    data["last_found"] = int(found_count)
    try:
        STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def restored_bytes():
    total = 0
    if not DELETED_LOG.exists():
        return 0
    try:
        for line in DELETED_LOG.read_text(encoding="utf-8").splitlines():
            try:
                total += int(json.loads(line).get("size") or 0)
            except Exception:
                continue
    except OSError:
        return total
    return total


def drive_stat_lines(drives):
    lines = []
    for root, kind in drives:
        try:
            usage = shutil.disk_usage(root)
            lines.append(
                f"  {root}  {kind}   {human_size(usage.free)} free of {human_size(usage.total)}"
            )
        except OSError:
            lines.append(f"  {root}  {kind}   size unavailable")
    return lines or ["  No local drives found"]


def has_launcher(path, limit=50):
    try:
        with os.scandir(path) as it:
            n = 0
            for ent in it:
                n += 1
                if n > limit:
                    break
                if ent.is_file() and ent.name.lower().endswith((".exe", ".lnk")):
                    return True
    except OSError:
        return False
    return False


def looks_personal(path, limit=40):
    files = 0
    media = 0
    try:
        with os.scandir(path) as it:
            for ent in it:
                if files >= limit:
                    break
                if not ent.is_file():
                    continue
                files += 1
                if Path(ent.name).suffix.lower() in MEDIA_EXT:
                    media += 1
    except OSError:
        return False
    return files >= 8 and media / files >= 0.6


def name_hit(folder_name, apps):
    folder = normalize(folder_name)
    if not folder or len(folder) < 3:
        return 0.0, ""
    best = 0.0
    why = ""
    for app in apps:
        app_name = app.get("norm") or ""
        if not app_name:
            continue
        if folder == app_name:
            return 1.0, app["name"]
        if folder in app_name or app_name in folder:
            if 0.8 > best:
                best = 0.8
                why = app["name"]
        elif folder.split()[0] == app_name.split()[0] and len(folder.split()[0]) >= 4:
            if 0.62 > best:
                best = 0.62
                why = app["name"]
    return best, why


def interesting(path):
    blob = str(path).lower()
    keys = ("cache", "temp", "tmp", "log", "crash", "installer", "update", "download", "shader", "gpu")
    return any(k in blob for k in keys)


def collect_roots(drive, include_pf):
    roots = []
    drive_path = Path(drive)
    users = drive_path / "Users"
    if users.is_dir():
        try:
            for user in users.iterdir():
                if not user.is_dir() or user.name.lower() in SKIP_USER:
                    continue
                for rel in ("AppData/Local", "AppData/Roaming", "AppData/LocalLow"):
                    p = user.joinpath(*rel.split("/"))
                    if p.is_dir():
                        roots.append(p)
        except OSError:
            pass
    for name in ("ProgramData",):
        p = drive_path / name
        if p.is_dir():
            roots.append(p)
    temp = Path(os.environ.get("TEMP", "")) if drive.upper().startswith("C:") else drive_path / "Temp"
    if str(temp).lower().startswith(drive.lower()) and temp.is_dir():
        roots.append(temp)
    windir_temp = drive_path / "Windows" / "Temp"
    if windir_temp.is_dir():
        roots.append(windir_temp)
    if include_pf:
        for name in ("Program Files", "Program Files (x86)"):
            p = drive_path / name
            if p.is_dir():
                roots.append(p)
    try:
        for ent in drive_path.iterdir():
            if not ent.is_dir() or ent.is_symlink():
                continue
            if ent.name.lower() in SKIP_TOP or ent.name.lower() in PERSONAL_NAMES:
                continue
            if is_blocked_name(ent.name) or is_nahimic(ent):
                continue
            roots.append(ent)
    except OSError:
        pass
    unique = []
    seen = set()
    for root in roots:
        key = str(root).lower()
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def saved_agent():
    try:
        data = json.loads(LINK_FILE.read_text(encoding="utf-8"))
        return data.get("model") or "hermes3"
    except Exception:
        return "hermes3"


def link_record():
    try:
        data = json.loads(LINK_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_agent(model, verified=False):
    payload = {"model": model, "endpoint": OLLAMA}
    if verified:
        payload["verified"] = datetime.now().isoformat(timespec="seconds")
    try:
        LINK_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass


def agent_write(text, newline=False):
    with _agent_lock:
        with AGENT_LOG.open("a", encoding="utf-8") as handle:
            handle.write(text)
            if newline:
                handle.write("\n")
            handle.flush()


def open_agent_window(model, drives):
    global _agent_window_started
    state = load_scan_state()
    last = state.get("last_scan") or "never"
    if state.get("last_found") is not None:
        last = f"{last}   ({state.get('last_found')} leftovers)"
    online = ollama_up()
    lines = [
        "Hello. I am the local leftover agent on this PC.",
        "I only recommend folders that have no program launcher and no installed app.",
        "A standalone .exe or shortcut means the program can still run. I will not recommend those.",
        "I cannot delete Windows, OEM, Nahimic, or anything a process is still using.",
        "",
        "Drives",
    ]
    lines.extend(drive_stat_lines(drives))
    lines.extend([
        "",
        "Last scan: " + last,
        "Space restored to the drive: " + human_size(restored_bytes()),
        "",
        "Ollama: " + ("online" if online else "not running. Click Link AI in the cleaner."),
        "Agent: " + (model or "hermes3"),
        "",
        "I will write my answer here after each search finishes. Not one word at a time.",
        "",
    ])
    with _agent_lock:
        AGENT_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
        if _agent_window_started:
            return
        safe = str(AGENT_LOG).replace("'", "''")
        command = (
            "$Host.UI.RawUI.WindowTitle = 'Leftover Agent'; "
            f"Get-Content -LiteralPath '{safe}' -Wait -Tail 80 -Encoding UTF8"
        )
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "Leftover Agent", PS, "-NoExit", "-NoProfile", "-Command", command],
            creationflags=CREATE_NO_WINDOW,
        )
        _agent_window_started = True


def prove_link(model):
    """Ask the selected agent to answer. True only if that model replies."""
    body = json.dumps({
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": "Reply with JSON only."},
            {"role": "user", "content": 'Reply with exactly {"link":"ok"}'},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA + "/api/chat", data=body, headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    content = ((data.get("message") or {}).get("content")) or ""
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {}
    ok = str(parsed.get("link") or "").lower() == "ok" or '"link":"ok"' in content.replace(" ", "").lower()
    return ok, content[:300]


def find_ollama():
    names = []
    local = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("ProgramFiles", "")
    pf86 = os.environ.get("ProgramFiles(x86)", "")
    for base in (Path(local) / "Programs" / "Ollama", Path(pf) / "Ollama", Path(pf86) / "Ollama"):
        names.append(base / "ollama.exe")
    for path in names:
        if path.is_file():
            return path
    try:
        proc = subprocess.run(
            ["where.exe", "ollama"], capture_output=True, text=True, timeout=8, creationflags=CREATE_NO_WINDOW,
        )
        for line in (proc.stdout or "").splitlines():
            found = Path(line.strip())
            if found.is_file():
                return found
    except Exception:
        pass
    return None


def ollama_tags():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        return [m.get("name") for m in data.get("models") or [] if m.get("name")]
    except Exception:
        return []


def start_ollama(exe):
    app = exe.with_name("ollama app.exe")
    if app.is_file():
        args = [str(app)]
    else:
        args = [str(exe), "serve"]
    subprocess.Popen(args, creationflags=CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for_ollama(seconds=20):
    import time
    for _ in range(seconds):
        tags = ollama_tags()
        if tags or ollama_up():
            return ollama_tags()
        time.sleep(1)
    return []


def ollama_up():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/version", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def forbidden_reason(path):
    text = str(path).lower().replace("/", "\\")
    if is_nahimic(path):
        return "Nahimic or A-Volute"
    for part in SYS_PARTS:
        if part in text:
            return "Windows system path"
    if "\\windowsapps\\" in text or text.rstrip("\\").endswith("\\windows"):
        return "Windows component"
    parts = [normalize(p) for p in Path(path).parts]
    for part in parts:
        if part in OEM_FOLDERS or part in BLOCK_EXACT:
            return "OEM, hardware, or Windows folder"
        if "nahimic" in part.replace(" ", "") or "avolute" in part.replace(" ", ""):
            return "Nahimic or A-Volute"
    if is_blocked_name(Path(path).name):
        return "protected folder name"
    return ""


def ai_double_check(folder, install_roots, procs, svcs):
    reason = forbidden_reason(folder)
    if reason:
        return reason
    if installed_owns(folder, install_roots):
        return "still owned by an installed app"
    if used_by(folder, procs) or used_by(folder, svcs):
        return "a process or service is still using it"
    if has_app_launcher(folder):
        return "still has a program launcher"
    if Path(folder).name.lower() in PERSONAL_NAMES or looks_personal(folder):
        return "looks like personal files"
    return ""


def pretty_reply(content):
    text = (content or "").strip()
    if not text:
        return "The agent returned nothing."
    try:
        return json.dumps(json.loads(text), indent=2)
    except Exception:
        return text


def ollama_review(model, folders, app_names):
    lines = []
    for item in folders:
        lines.append(f"{item['path']} | {human_size(item['size'])} | launcher={item['has_exe']}")
    user = (
        "Installed apps that must be kept:\n" + "\n".join(app_names[:120])
        + "\n\nDo not nominate a folder that belongs to one of those apps."
        + "\nDo not nominate a folder that has a standalone launcher."
        + "\nFolders you may consider:\n" + "\n".join(lines)
    )
    body = json.dumps({
        "model": model,
        "stream": True,
        "format": "json",
        "messages": [
            {"role": "system", "content": AI_GUIDELINES},
            {"role": "user", "content": user},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA + "/api/chat", data=body, headers={"Content-Type": "application/json"})
    parts = []
    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            piece = ((event.get("message") or {}).get("content")) or ""
            if piece:
                parts.append(piece)
            if event.get("done"):
                break
    content = "".join(parts)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {}
    return parsed.get("leftovers") or [], pretty_reply(content)


def report_crash(text):
    crash = APP_DIR / "crash.txt"
    cause = text.strip().splitlines()[-1] if text.strip() else "unknown"
    body = f"CRASH FILE: {crash}\nWHEN: {datetime.now():%Y-%m-%d %H:%M:%S}\nCAUSE: {cause}\n\n{text}\n"
    print(body)
    try:
        crash.write_text(body, encoding="utf-8")
        os.startfile(str(crash))
    except Exception:
        pass
    try:
        os.system("pause")
    except Exception:
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{VERSION}")
        self._apply_icon()
        self.geometry("1180x760")
        self.minsize(980, 600)
        self.drives = list_drives()
        self.drive_vars = {}
        self.rows = []
        self.deleted_rows = []
        self.selected = set()
        self.iid_path = {}
        self.dry_run = tk.BooleanVar(value=True)
        self.include_pf = tk.BooleanVar(value=True)
        self.use_ai = tk.BooleanVar(value=True)
        self.model_var = tk.StringVar(value=saved_agent())
        self._style()
        self._build()
        self._log(f"Log: {LOG_FILE}")
        self._log("Admin: " + ("yes" if is_admin() else "no"))
        self._log("Program Files and Program Files (x86) are included. Installed apps stay off the list.")
        self._log("Dry-run is ON. The agent window opens with this program.")
        self.after(200, self.refresh_deleted)
        self.after(300, self.open_agent_at_launch)
        self.after(400, self.poll_ai)

    def _apply_icon(self):
        if getattr(sys, "frozen", False):
            icon = Path(getattr(sys, "_MEIPASS", "")) / "leftover_icon_32.ico"
        else:
            icon = Path(__file__).resolve().parent / "leftover_icon_32.ico"
        if not icon.is_file():
            return
        try:
            self.iconbitmap(default=str(icon))
        except Exception:
            try:
                self.iconbitmap(str(icon))
            except Exception:
                pass

    def _style(self):
        self.configure(bg=DARK["bg"])
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        bg, fg, field, btn = DARK["bg"], DARK["fg"], DARK["field"], DARK["button"]
        style.configure(".", background=bg, foreground=fg, fieldbackground=field)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TButton", background=btn, foreground=fg, padding=6)
        style.map("TButton", background=[("active", "#505050")])
        style.configure("TCheckbutton", background=bg, foreground=fg)
        style.configure("TEntry", fieldbackground=field, foreground=fg)
        style.configure("Treeview", background=field, foreground=fg, fieldbackground=field, rowheight=26)
        style.configure("Treeview.Heading", background=btn, foreground=fg, relief="flat")
        style.map("Treeview", background=[("selected", DARK["select"])], foreground=[("selected", "#ffffff")])
        style.configure("TLabelframe", background=bg, foreground=fg)
        style.configure("TLabelframe.Label", background=bg, foreground=fg)
        style.configure("TNotebook", background=bg)
        style.configure("TNotebook.Tab", background=btn, foreground=fg, padding=[10, 4])
        style.map("TNotebook.Tab", background=[("selected", field)])

    def _build(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)
        ttk.Button(top, text="Scan", command=self.scan).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="Delete selected", command=self.delete_selected).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="Refresh deleted", command=self.refresh_deleted).pack(side=tk.LEFT, padx=3)
        ttk.Checkbutton(top, text="Dry-run", variable=self.dry_run).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(top, text="Program Files + (x86)", variable=self.include_pf).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(top, text="Local AI", variable=self.use_ai).pack(side=tk.LEFT, padx=4)
        ttk.Label(top, text="Agent").pack(side=tk.LEFT, padx=(8, 2))
        self.agent = ttk.Combobox(top, textvariable=self.model_var, width=22, state="readonly")
        self.agent.pack(side=tk.LEFT)
        self.agent.bind("<<ComboboxSelected>>", self.on_agent_change)
        ttk.Button(top, text="Link AI", command=self.link_ai).pack(side=tk.LEFT, padx=4)
        self.ai_status = ttk.Label(top, text="AI not checked")
        self.ai_status.pack(side=tk.LEFT, padx=6)
        if not is_admin():
            ttk.Button(top, text="Relaunch as admin", command=self.on_relaunch).pack(side=tk.RIGHT, padx=3)

        drive_box = ttk.LabelFrame(self, text="Drives", padding=6)
        drive_box.pack(fill=tk.X, padx=8, pady=4)
        if not self.drives:
            ttk.Label(drive_box, text="No local drives found").pack(side=tk.LEFT)
        for root, kind in self.drives:
            var = tk.BooleanVar(value=root.upper().startswith("C:"))
            self.drive_vars[root] = var
            ttk.Checkbutton(drive_box, text=f"{root}  {kind}", variable=var).pack(side=tk.LEFT, padx=8)

        self.note = ttk.Label(self, text="Protected, Nahimic, and anything with a running process or installed app is not listed.", padding=(8, 0))
        self.note.pack(fill=tk.X)

        self.book = ttk.Notebook(self)
        self.book.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        left = ttk.Frame(self.book)
        self.book.add(left, text="  Leftovers  ")
        cols = ("sel", "size", "confidence", "source", "reason")
        self.tree = ttk.Treeview(left, columns=cols, show="tree headings")
        self.tree.heading("#0", text="Path")
        self.tree.heading("sel", text="[ ]")
        self.tree.heading("size", text="Size")
        self.tree.heading("confidence", text="Confidence")
        self.tree.heading("source", text="Found by")
        self.tree.heading("reason", text="Why")
        self.tree.column("#0", width=460, stretch=True)
        self.tree.column("sel", width=40, anchor=tk.CENTER, stretch=False)
        self.tree.column("size", width=90, anchor=tk.E, stretch=False)
        self.tree.column("confidence", width=90, anchor=tk.CENTER, stretch=False)
        self.tree.column("source", width=80, anchor=tk.CENTER, stretch=False)
        self.tree.column("reason", width=320, stretch=True)
        vsb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.LEFT, fill=tk.Y)
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<Double-1>", self._open_row)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<ButtonRelease-3>", self._on_right_click)
        self.tree.bind("<Shift-F10>", self._on_context_key)
        self.tree.bind("<App>", self._on_context_key)
        self._build_context_menu()
        self.tree.tag_configure("AI", foreground=DARK["warn"])
        self.tree.tag_configure("Rules", foreground=DARK["ok"])

        deleted = ttk.Frame(self.book)
        self.book.add(deleted, text="  Recently deleted  ")
        self.del_tree = ttk.Treeview(deleted, columns=("size", "when", "from"), show="tree headings")
        self.del_tree.heading("#0", text="Name")
        self.del_tree.heading("size", text="Size")
        self.del_tree.heading("when", text="When")
        self.del_tree.heading("from", text="Original location")
        self.del_tree.column("#0", width=260, stretch=True)
        self.del_tree.column("size", width=90, anchor=tk.E, stretch=False)
        self.del_tree.column("when", width=180, stretch=False)
        self.del_tree.column("from", width=460, stretch=True)
        dsb = ttk.Scrollbar(deleted, orient=tk.VERTICAL, command=self.del_tree.yview)
        self.del_tree.configure(yscrollcommand=dsb.set)
        self.del_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dsb.pack(side=tk.LEFT, fill=tk.Y)

        log_tab = ttk.Frame(self.book)
        self.book.add(log_tab, text="  Log  ")
        self.log = scrolledtext.ScrolledText(log_tab, state="disabled", wrap=tk.WORD, bg=DARK["field"], fg=DARK["fg"], insertbackground=DARK["fg"])
        self.log.pack(fill=tk.BOTH, expand=True)

        self.status = ttk.Label(self, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _log(self, msg):
        logger.info(msg)
        def write():
            self.log.configure(state="normal")
            self.log.insert(tk.END, msg + "\n")
            self.log.see(tk.END)
            self.log.configure(state="disabled")
        try:
            self.after(0, write)
        except tk.TclError:
            pass

    def _set_status(self, text):
        self.after(0, lambda: self.status.configure(text=text))

    def on_relaunch(self):
        if relaunch_as_admin():
            self.destroy()
        else:
            messagebox.showwarning("Admin", "Windows did not elevate.")

    def on_agent_change(self, _event=None):
        name = self.model_var.get().strip()
        if name:
            save_agent(name, verified=False)
            self._log("Agent set to " + name + ". Click Link AI to prove it answers.")
            self.ai_status.configure(text="AI online, not proved: " + name)

    def open_agent_at_launch(self):
        model = self.model_var.get().strip() or "hermes3"
        drives = list(self.drives)

        def work():
            try:
                open_agent_window(model, drives)
                self._log("Agent window opened. Greeting, drive space, last scan, and restored space are there.")
            except Exception as exc:
                self._log("Could not open the agent window: " + str(exc))

        threading.Thread(target=work, daemon=True).start()

    def poll_ai(self):
        def work():
            tags = ollama_tags()
            up = bool(tags) or ollama_up()
            saved = link_record()
            def apply():
                if tags:
                    self.agent["values"] = tags
                    current = self.model_var.get().strip()
                    if current not in tags:
                        self.model_var.set(tags[0])
                        current = tags[0]
                    proved = saved.get("verified") and saved.get("model") == current
                    if proved:
                        self.ai_status.configure(text="AI link established: " + current)
                    else:
                        self.ai_status.configure(text="AI online, not proved: " + current)
                elif up:
                    self.ai_status.configure(text="AI running, no agent pulled")
                else:
                    self.ai_status.configure(text="AI offline")
                self.after(20000, self.poll_ai)
            self.after(0, apply)
        threading.Thread(target=work, daemon=True).start()

    def link_ai(self):
        self._set_status("Linking local AI...")
        self._log("AI setup: looking for Ollama...")

        def work():
            exe = find_ollama()
            if exe is None:
                def missing():
                    self._log("Ollama is not installed.")
                    if messagebox.askyesno(
                        "Install Ollama",
                        "Ollama is not installed on this PC.\n\n"
                        "Install it now with winget? This can take a few minutes.",
                    ):
                        threading.Thread(target=self._install_ollama, daemon=True).start()
                    else:
                        self.ai_status.configure(text="AI not installed")
                self.after(0, missing)
                return
            self._log("Found " + str(exe))
            tags = ollama_tags()
            if not tags and not ollama_up():
                self._log("Ollama is installed but not running. Starting it...")
                try:
                    start_ollama(exe)
                except Exception as exc:
                    self._log("Could not start Ollama: " + str(exc))
                tags = wait_for_ollama(20)
            if not ollama_up() and not tags:
                def down():
                    self.ai_status.configure(text="AI offline")
                    messagebox.showwarning("Ollama", "Ollama was found but the local link did not open.")
                self.after(0, down)
                return
            if not tags:
                def pull():
                    self._log("Ollama is running but no agent is installed.")
                    if messagebox.askyesno("Pull agent", "No local agent is installed. Download hermes3 now?"):
                        threading.Thread(target=lambda: self._pull_agent(exe, "hermes3"), daemon=True).start()
                    else:
                        self.ai_status.configure(text="AI running, no agent")
                self.after(0, pull)
                return
            current = self.model_var.get().strip()
            chosen = current if current in tags else tags[0]
            self._log("Asking " + chosen + " to answer on " + OLLAMA)
            try:
                ok, reply = prove_link(chosen)
            except Exception as exc:
                ok, reply = False, str(exc)
            def ready():
                self.agent["values"] = tags
                self.model_var.set(chosen)
                if not ok:
                    save_agent(chosen, verified=False)
                    self.ai_status.configure(text="AI online, not proved: " + chosen)
                    self._log("Link not established. Agent reply: " + reply)
                    self._set_status("Link not established")
                    messagebox.showwarning(
                        "Link not established",
                        chosen + " did not answer.\n\n" + reply,
                    )
                    return
                save_agent(chosen, verified=True)
                self.ai_status.configure(text="AI link established: " + chosen)
                self._log("AI link established. " + chosen + " answered. Agents: " + ", ".join(tags))
                self._set_status("AI link established: " + chosen)
                messagebox.showinfo(
                    "Link established",
                    chosen + " answered on this PC.\n\n"
                    "The link is saved in ai_link.json.\n"
                    "Windows, OEM, Nahimic, and installed apps are still refused.",
                )
            self.after(0, ready)

        threading.Thread(target=work, daemon=True).start()

    def _install_ollama(self):
        self._log("Running winget install Ollama.Ollama")
        try:
            proc = subprocess.run(
                ["winget", "install", "--id", "Ollama.Ollama", "-e",
                 "--accept-package-agreements", "--accept-source-agreements"],
                capture_output=True, text=True, timeout=600, creationflags=CREATE_NO_WINDOW,
            )
            self._log((proc.stdout or "")[-1500:])
            if proc.returncode != 0:
                self._log((proc.stderr or "")[-800:])
                self.after(0, lambda: messagebox.showwarning("Ollama", "winget did not finish the install. See the log."))
                return
        except Exception as exc:
            self._log("winget failed: " + str(exc))
            self.after(0, lambda: messagebox.showwarning("Ollama", str(exc)))
            return
        self.after(0, self.link_ai)

    def _pull_agent(self, exe, name):
        self._log("Downloading agent " + name)
        self._set_status("Downloading " + name + "...")
        try:
            proc = subprocess.run(
                [str(exe), "pull", name],
                capture_output=True, text=True, timeout=1800, creationflags=CREATE_NO_WINDOW,
            )
            self._log((proc.stdout or proc.stderr or "")[-1500:])
            if proc.returncode != 0:
                self.after(0, lambda: messagebox.showwarning("Agent", "The download did not finish. See the log."))
                return
        except Exception as exc:
            self._log("Pull failed: " + str(exc))
            self.after(0, lambda: messagebox.showwarning("Agent", str(exc)))
            return
        self.after(0, self.link_ai)

    def _fill(self):
        self.tree.delete(*self.tree.get_children())
        self.iid_path.clear()
        for row in self.rows:
            mark = "X" if row["path"] in self.selected else ""
            iid = self.tree.insert(
                "", "end", text=row["path"],
                values=(mark, human_size(row["size"]), f"{row['confidence']:.0%}", row["source"], row["reason"]),
                tags=(row["source"],),
            )
            self.iid_path[iid] = row["path"]

    def _build_context_menu(self):
        self.ctx_path = ""
        self.ctx = tk.Menu(
            self, tearoff=0, bg=DARK["field"], fg=DARK["fg"],
            activebackground=DARK["select"], activeforeground="#ffffff",
        )
        self.ctx.add_command(label="Select / deselect", command=self.ctx_toggle)
        self.ctx.add_separator()
        self.ctx.add_command(label="Open file location", command=self.ctx_open)
        self.ctx.add_command(label="Copy path", command=self.ctx_copy)
        self.ctx.add_separator()
        self.ctx.add_command(label="Run leftover uninstaller...", command=self.ctx_unins)
        self.ctx.add_separator()
        self.ctx.add_command(label="Delete (Recycle Bin)", command=self.ctx_delete)

    def _show_menu(self, iid, x_root, y_root):
        if not iid:
            return
        path = self.iid_path.get(iid)
        if not path:
            return
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        self.ctx_path = path
        try:
            self.ctx.tk_popup(int(x_root), int(y_root))
        except tk.TclError:
            self.ctx.post(int(x_root), int(y_root))

    def _on_right_click(self, event):
        iid = self.tree.identify_row(event.y) or self.tree.identify("item", event.x, event.y)
        self._show_menu(iid, event.x_root, event.y_root)
        return "break"

    def _on_context_key(self, event):
        sel = self.tree.selection()
        iid = sel[0] if sel else ""
        self._show_menu(iid, self.winfo_pointerx(), self.winfo_pointery())
        return "break"

    def _row_for(self, path):
        for row in self.rows:
            if row["path"] == path:
                return row
        return None

    def _iid_for(self, path):
        for iid, stored in self.iid_path.items():
            if stored == path:
                return iid
        return ""

    def ctx_toggle(self):
        path = self.ctx_path
        iid = self._iid_for(path)
        if not path or not iid:
            return
        if path in self.selected:
            self.selected.discard(path)
            self.tree.set(iid, "sel", "")
        else:
            self.selected.add(path)
            self.tree.set(iid, "sel", "X")

    def ctx_open(self):
        path = self.ctx_path
        if not path:
            return
        target = Path(path)
        if not target.exists():
            target = target.parent
        if target.exists():
            os.startfile(str(target))
        else:
            messagebox.showinfo("Missing", "That path is no longer there.")

    def ctx_copy(self):
        if not self.ctx_path:
            return
        self.clipboard_clear()
        self.clipboard_append(self.ctx_path)
        self._log("Copied: " + self.ctx_path)

    def ctx_unins(self):
        row = self._row_for(self.ctx_path)
        unins = (row or {}).get("uninstaller") or ""
        if not unins and self.ctx_path:
            found = find_uninstallers(self.ctx_path, 1)
            unins = found[0] if found else ""
        if not unins:
            messagebox.showinfo("No uninstaller", "No leftover uninstaller was found in this folder.")
            return
        if not messagebox.askyesno("Run leftover uninstaller", "This will launch:\n\n" + unins + "\n\nContinue?"):
            return
        ok, msg = launch_uninstaller(f'"{unins}"', dry_run=self.dry_run.get())
        self._log(msg)
        if not ok:
            messagebox.showerror("Uninstaller", msg)

    def ctx_delete(self):
        if not self.ctx_path:
            return
        self.selected = {self.ctx_path}
        iid = self._iid_for(self.ctx_path)
        for other, stored in list(self.iid_path.items()):
            self.tree.set(other, "sel", "X" if stored == self.ctx_path else "")
        if iid:
            self.tree.selection_set(iid)
        self.delete_selected()

    def _on_click(self, event):
        if self.tree.identify_column(event.x) != "#1":
            return
        iid = self.tree.identify_row(event.y)
        path = self.iid_path.get(iid)
        if not path:
            return
        if path in self.selected:
            self.selected.discard(path)
            self.tree.set(iid, "sel", "")
        else:
            self.selected.add(path)
            self.tree.set(iid, "sel", "X")
        return "break"

    def _open_row(self, event):
        iid = self.tree.identify_row(event.y)
        path = self.iid_path.get(iid)
        if not path:
            return
        target = Path(path)
        if not target.exists():
            target = target.parent
        if target.exists():
            os.startfile(str(target))

    def _write_exe_stops(self, stopped):
        agent_write("", newline=True)
        agent_write(
            f"Scan stopped in {len(stopped)} folders because a program .exe or shortcut was found.",
            newline=True,
        )
        agent_write("Those folders were not scanned further and are not recommended for deletion.", newline=True)
        if not stopped:
            agent_write("No folder was stopped for an .exe.", newline=True)
            return
        for folder, exe in stopped:
            agent_write("STOPPED  " + exe + "   " + folder, newline=True)

    def _exe_stop_dialog(self, stopped):
        if not stopped:
            messagebox.showinfo(
                "Scan complete",
                "Scan finished.\n\nNo folder was stopped because of an .exe.",
            )
            return
        lines = [exe + "   " + folder for folder, exe in stopped[:30]]
        extra = ""
        if len(stopped) > 30:
            extra = f"\n\n... and {len(stopped) - 30} more.\nThe full list is in the Leftover Agent window."
        messagebox.showinfo(
            "Scan stopped at program files",
            f"Scan finished.\n\n"
            f"Scanning stopped in {len(stopped)} folders because an .exe or shortcut was found.\n"
            "Those programs were not scanned further and are not listed for deletion.\n\n"
            + "\n".join(lines)
            + extra,
        )

    def scan(self):
        drives = [d for d, var in self.drive_vars.items() if var.get()]
        if not drives:
            messagebox.showinfo("Scan", "Select at least one drive.")
            return
        include_pf = self.include_pf.get()
        use_ai = self.use_ai.get()
        model = self.model_var.get().strip() or "hermes3"
        self.selected.clear()
        self._set_status("Scanning...")
        self._log("Scan started: " + ", ".join(drives))

        def work():
            try:
                self._scan_work(drives, include_pf, use_ai, model)
            except Exception:
                err = traceback.format_exc()
                self._log(err)
                self.after(0, lambda: messagebox.showerror("Scan", err[-800:]))

        threading.Thread(target=work, daemon=True).start()

    def _scan_work(self, drives, include_pf, use_ai, model):
        self._log("Reading installed apps...")
        apps, err = ps_json(APPS_PS, timeout=120)
        if err:
            self._log(err.strip()[:400])
        for app in apps:
            app["norm"] = normalize(app.get("Name") or app.get("name") or "")
            app["name"] = app.get("Name") or app.get("name") or ""
            app["location"] = app.get("Location") or app.get("location") or ""
        install_roots = specific_installs(apps)
        self._log(f"Installed apps: {len(apps)}")

        self._log("Reading processes and services...")
        runtime, rerr = ps_json(RUNTIME_PS, timeout=120)
        procs, svcs = [], []
        if runtime:
            blob = runtime[0]
            raw_procs = blob.get("Processes") or []
            raw_svcs = blob.get("Services") or []
            if isinstance(raw_procs, str):
                raw_procs = [raw_procs]
            if isinstance(raw_svcs, str):
                raw_svcs = [raw_svcs]
            procs = [p for p in raw_procs if p]
            svcs = [p for p in raw_svcs if p]
        if rerr:
            self._log(rerr.strip()[:400])
        self._log(f"Process paths: {len(procs)}   Service paths: {len(svcs)}")

        found = []
        unsure = []
        seen = set()
        kept_launchers = 0
        stopped_for_exe = []
        for drive in drives:
            roots = collect_roots(drive, include_pf)
            self._log(f"{drive}  {len(roots)} locations, Program Files included: {include_pf}")
            for root in roots:
                self._set_status(f"Scanning {root}")
                try:
                    children = list(root.iterdir())
                except OSError as exc:
                    self._log(f"Skip {root}: {exc}")
                    continue
                for child in children:
                    try:
                        if not child.is_dir() or child.is_symlink():
                            continue
                    except OSError:
                        continue
                    key = str(child).lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    if is_blocked_name(child.name) or is_nahimic(child):
                        continue
                    if child.name.lower() in PERSONAL_NAMES or looks_personal(child):
                        continue
                    if installed_owns(child, install_roots):
                        continue
                    if used_by(child, procs) or used_by(child, svcs):
                        continue
                    exe_hit = first_app_exe(child)
                    if exe_hit:
                        kept_launchers += 1
                        stopped_for_exe.append((str(child), exe_hit))
                        continue
                    score, match = name_hit(child.name, apps)
                    if score >= 0.62:
                        continue
                    size = folder_size(child)
                    if size < MIN_SIZE:
                        continue
                    launcher = has_launcher(child)
                    reason = []
                    conf = 0.45
                    if score < 0.2:
                        conf += 0.2
                        reason.append("no installed app match")
                    else:
                        reason.append(f"weak match {match}")
                    if interesting(child):
                        conf += 0.15
                        reason.append("cache or temp")
                    if not launcher:
                        conf += 0.1
                        reason.append("no program file")
                    if "program files" in key:
                        conf += 0.1
                        reason.append("left in Program Files")
                    if size > 50 * 1024 * 1024:
                        conf += 0.05
                    conf = min(conf, 0.95)
                    item = {
                        "path": str(child),
                        "size": size,
                        "confidence": conf,
                        "source": "Rules",
                        "reason": ", ".join(reason),
                        "has_exe": launcher,
                        "uninstaller": "",
                    }
                    if conf >= 0.7:
                        found.append(item)
                    else:
                        unsure.append(item)

        found_paths = {r["path"].lower() for r in found}
        if use_ai:
            tags = ollama_tags()
            chosen = model if model in tags or any(model.split(":")[0] in t for t in tags) else (tags[0] if tags else model)
            agent_write("", newline=True)
            agent_write("Scan update", newline=True)
            agent_write(
                f"Rules kept {kept_launchers} folders because they still have a program launcher.",
                newline=True,
            )
            agent_write("Those stay installed. They are not recommended for deletion.", newline=True)
            if not unsure:
                agent_write("Nothing extra for the agent to review.", newline=True)
            elif not tags:
                agent_write("Ollama is not running, so the agent cannot search.", newline=True)
                self._log("Local AI skipped. Ollama is not running on this PC.")
            else:
                if chosen != model:
                    self._log(f"Model {model} not found. Using {chosen}.")
                    agent_write("Using " + chosen + " because " + model + " is not installed.", newline=True)
                pool = unsure[:200]
                self._log(f"AI reviewing {len(pool)} folders the rules did not list...")
                agent_write(f"Searching {len(pool)} folders. The answer will appear when the search finishes.", newline=True)
                by_path = {r["path"].lower(): r for r in pool}
                added = 0
                for start in range(0, len(pool), 25):
                    batch = pool[start:start + 25]
                    number = start // 25 + 1
                    self._set_status(f"Local AI batch {number}")
                    agent_write("", newline=True)
                    agent_write(f"----- batch {number} searching -----", newline=True)
                    for item in batch:
                        agent_write(item["path"], newline=True)
                    try:
                        ideas, reply = ollama_review(
                            chosen, batch, [a["name"] for a in apps if a.get("name")],
                        )
                    except Exception as exc:
                        self._log(f"AI batch failed: {exc}")
                        agent_write("Agent failed: " + str(exc), newline=True)
                        break
                    agent_write("", newline=True)
                    agent_write(f"----- batch {number} finished -----", newline=True)
                    agent_write(reply, newline=True)
                    agent_write("", newline=True)
                    agent_write("Double-check:", newline=True)
                    for idea in ideas:
                        path = (idea.get("path") or "").lower()
                        row = by_path.get(path)
                        if not row or path in found_paths:
                            agent_write("ignored, not one of the folders sent", newline=True)
                            continue
                        folder = Path(row["path"])
                        why = ai_double_check(folder, install_roots, procs, svcs)
                        if why:
                            self._log(f"AI double-check refused {folder.name}: {why}")
                            agent_write("refused " + folder.name + ": " + why, newline=True)
                            continue
                        try:
                            ai_conf = float(idea.get("confidence") or 0.6)
                        except (TypeError, ValueError):
                            ai_conf = 0.6
                        row["confidence"] = min(max(ai_conf, 0.55), 0.8)
                        row["source"] = "AI"
                        row["reason"] = (idea.get("reason") or "local model marked this as leftover")[:180]
                        found.append(row)
                        found_paths.add(path)
                        added += 1
                        agent_write("kept " + folder.name, newline=True)
                self._log(f"AI added {added} folder(s).")
                agent_write("", newline=True)
                agent_write(f"Done. Agent added {added} folder(s).", newline=True)

        found.sort(key=lambda r: r["size"], reverse=True)
        save_scan_state(len(found))
        self._write_exe_stops(stopped_for_exe)
        agent_write("", newline=True)
        agent_write("Scan finished: " + datetime.now().isoformat(timespec="seconds"), newline=True)
        agent_write(f"Leftovers listed: {len(found)}", newline=True)
        agent_write("Space restored to the drive: " + human_size(restored_bytes()), newline=True)
        self.rows = found
        stopped_copy = list(stopped_for_exe)

        def show():
            self._fill()
            msg = f"{len(found)} leftovers on {len(drives)} drive(s). Stopped {len(stopped_copy)} folders at an .exe."
            self.status.configure(text=msg)
            self._log("Scan finished. " + msg)
            self._exe_stop_dialog(stopped_copy)
        self.after(0, show)

    def refresh_deleted(self):
        def work():
            rows = []
            if DELETED_LOG.exists():
                try:
                    for line in DELETED_LOG.read_text(encoding="utf-8").splitlines()[-200:]:
                        item = json.loads(line)
                        item["where"] = "This tool"
                        rows.append(item)
                except Exception as exc:
                    self._log(f"Could not read delete log: {exc}")
            data, err = ps_json(RECYCLE_PS, timeout=60)
            if err:
                self._log(err.strip()[:300])
            for item in data:
                name = item.get("Name") or ""
                if not name:
                    continue
                suffix = Path(name).suffix.lower()
                if suffix in MEDIA_EXT:
                    continue
                rows.append({
                    "name": name,
                    "size": item.get("Size") or 0,
                    "when": item.get("Deleted") or "",
                    "from": item.get("From") or "",
                    "where": "Recycle Bin",
                })
            def show():
                self.del_tree.delete(*self.del_tree.get_children())
                for item in rows:
                    self.del_tree.insert(
                        "", "end",
                        text=item.get("name") or Path(item.get("path", "")).name,
                        values=(human_size(item.get("size") or 0), item.get("when") or item.get("where") or "", item.get("from") or item.get("path") or ""),
                    )
                self._log(f"Recently deleted listed: {len(rows)}")
            self.after(0, show)
        threading.Thread(target=work, daemon=True).start()

    def delete_selected(self):
        paths = [p for p in self.selected if any(r["path"] == p for r in self.rows)]
        if not paths:
            messagebox.showinfo("Delete", "Select one or more leftovers first.")
            return
        blocked = [p for p in paths if is_nahimic(p) or is_blocked_name(Path(p).name)]
        paths = [p for p in paths if p not in blocked]
        if blocked:
            self._log("Refused protected: " + "; ".join(blocked))
        if not paths:
            messagebox.showinfo("Protected", "Those folders are protected.")
            return
        mode = "DRY-RUN" if self.dry_run.get() else "DELETE"
        preview = "\n".join(paths[:25])
        if not messagebox.askyesno("Confirm", f"{mode} {len(paths)} folder(s)\n\n{preview}\n\nContinue?"):
            return
        if not self.dry_run.get() and not is_admin():
            if messagebox.askyesno("Admin", "Program Files deletes usually need Administrator. Relaunch now?"):
                self.on_relaunch()
                return
        dry = self.dry_run.get()

        def work():
            ok = 0
            for path in paths:
                if is_nahimic(path) or is_blocked_name(Path(path).name):
                    self._log("Refused " + path)
                    continue
                if dry:
                    self._log("[DRY-RUN] Would recycle " + path)
                    ok += 1
                    continue
                code, out, err = run_powershell(
                    "\n".join([
                        "$ErrorActionPreference = 'Stop'",
                        "Add-Type -AssemblyName Microsoft.VisualBasic",
                        f"$path = '{path.replace(chr(39), chr(39)*2)}'",
                        "if (Test-Path -LiteralPath $path -PathType Container) {",
                        "  [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($path, 'OnlyErrorDialogs', 'SendToRecycleBin')",
                        "} else {",
                        "  [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($path, 'OnlyErrorDialogs', 'SendToRecycleBin')",
                        "}",
                        "Write-Output 'DELETED_OK'",
                    ]),
                    timeout=120,
                )
                good = "DELETED_OK" in out and code == 0
                self._log(("Recycled " if good else "Failed ") + path + " " + (err or "")[:200])
                if good:
                    ok += 1
                    try:
                        with DELETED_LOG.open("a", encoding="utf-8") as handle:
                            handle.write(json.dumps({
                                "name": Path(path).name,
                                "path": path,
                                "when": datetime.now().isoformat(timespec="seconds"),
                                "size": next((r["size"] for r in self.rows if r["path"] == path), 0),
                            }) + "\n")
                    except OSError:
                        pass
            def finish():
                self._log(f"Finished {ok}/{len(paths)}")
                self.status.configure(text=f"Finished {ok}/{len(paths)}")
                if not dry:
                    gone = {p.lower() for p in paths}
                    self.rows = [r for r in self.rows if r["path"].lower() not in gone]
                    self.selected.clear()
                    self._fill()
                    self.refresh_deleted()
            self.after(0, finish)
        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    try:
        print(f"Starting {APP_NAME} {VERSION}")
        App().mainloop()
    except Exception:
        report_crash(traceback.format_exc())
        sys.exit(1)

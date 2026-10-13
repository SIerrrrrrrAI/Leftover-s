#!/usr/bin/env python3
"""
Leftover's Setup  v1.8.0

Windows setup wizard. Build it on Windows with build_exe.bat.
The finished file is dist\Leftover's Setup.exe.

The wizard asks before it installs anything.
Python is optional. The cleaner exe already contains Python.
Ollama and the hermes3 model are only needed for the local agent.
"""

import os
import sys
import shutil
import threading
import subprocess
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_NAME = "Leftover's"
EXE_NAME = "Leftover's.exe"
VERSION = "0.8.0"
CREATE_NO_WINDOW = 0x08000000
DARK = {
    "bg": "#1b1b1b", "fg": "#e6e6e6", "field": "#2a2a2a",
    "button": "#3a3a3a", "select": "#0a84ff",
}


def cleaner_payload():
    names = []
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", ""))
        names.append(base / EXE_NAME)
        names.append(Path(sys.executable).resolve().parent / EXE_NAME)
    else:
        here = Path(__file__).resolve().parent
        names.append(here / "dist" / EXE_NAME)
        names.append(here / EXE_NAME)
    for path in names:
        if path.is_file():
            return path
    return None


class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} Setup v{VERSION}")
        self._apply_icon()
        self.geometry("760x560")
        self.minsize(680, 500)
        self.configure(bg=DARK["bg"])
        self.payload = cleaner_payload()
        default_dir = str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Leftover's")
        self.install_dir = tk.StringVar(value=default_dir)
        self.want_python = tk.BooleanVar(value=False)
        self.want_ollama = tk.BooleanVar(value=True)
        self.want_model = tk.BooleanVar(value=True)
        self.want_desktop = tk.BooleanVar(value=True)
        self.want_start = tk.BooleanVar(value=True)
        self.launch_after = tk.BooleanVar(value=True)
        self.page = 0
        self._style()
        self._build()
        self.show_page(0)

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
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        bg, fg, field, btn = DARK["bg"], DARK["fg"], DARK["field"], DARK["button"]
        style.configure(".", background=bg, foreground=fg, fieldbackground=field)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TButton", background=btn, foreground=fg, padding=8)
        style.map("TButton", background=[("active", "#505050")])
        style.configure("TCheckbutton", background=bg, foreground=fg)
        style.configure("TEntry", fieldbackground=field, foreground=fg)
        style.configure("Horizontal.TProgressbar", background=DARK["select"], troughcolor=field)

    def _build(self):
        self.body = ttk.Frame(self, padding=18)
        self.body.pack(fill=tk.BOTH, expand=True)
        bar = ttk.Frame(self, padding=(18, 0, 18, 16))
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.back_btn = ttk.Button(bar, text="Back", command=self.back)
        self.back_btn.pack(side=tk.LEFT)
        self.next_btn = ttk.Button(bar, text="Next", command=self.next)
        self.next_btn.pack(side=tk.RIGHT)
        self.cancel_btn = ttk.Button(bar, text="Cancel", command=self.destroy)
        self.cancel_btn.pack(side=tk.RIGHT, padx=8)

        self.pages = []
        self.pages.append(self._welcome())
        self.pages.append(self._choices())
        self.pages.append(self._progress())
        self.pages.append(self._done())

    def _welcome(self):
        page = ttk.Frame(self.body)
        ttk.Label(page, text=APP_NAME, font=("Segoe UI", 20)).pack(anchor=tk.W)
        ttk.Label(page, text=f"Setup wizard  v{VERSION}", font=("Segoe UI", 11)).pack(anchor=tk.W, pady=(0, 16))
        text = (
            "This installs Leftover's on this PC.\n\n"
            "The cleaner is one program file. It already contains Python, so you do not need to install Python to run it.\n\n"
            "The next page asks before it installs anything else:\n"
            "  Python 3.12, only if you also want to run the .py script\n"
            "  Ollama, the local AI service\n"
            "  hermes3, the local model. This download is several GB\n\n"
            "Nothing is installed until you click Install."
        )
        ttk.Label(page, text=text, justify=tk.LEFT, wraplength=680).pack(anchor=tk.W)
        if self.payload is None:
            ttk.Label(
                page,
                text="The cleaner exe was not found next to this setup. Build it with build_exe.bat first.",
                wraplength=680,
                foreground="#e0a100",
            ).pack(anchor=tk.W, pady=(16, 0))
        else:
            ttk.Label(page, text="Cleaner found:\n" + str(self.payload), wraplength=680).pack(anchor=tk.W, pady=(16, 0))
        return page

    def _choices(self):
        page = ttk.Frame(self.body)
        ttk.Label(page, text="Choose what to install", font=("Segoe UI", 16)).pack(anchor=tk.W, pady=(0, 12))

        row = ttk.Frame(page)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Folder").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.install_dir, width=62).pack(side=tk.LEFT, padx=8)
        ttk.Button(row, text="Browse", command=self.browse).pack(side=tk.LEFT)

        ttk.Checkbutton(
            page,
            text="Install Python 3.12  (optional — the cleaner exe does not need it)",
            variable=self.want_python,
        ).pack(anchor=tk.W, pady=(14, 4))
        ttk.Checkbutton(
            page,
            text="Install Ollama  (required for the local AI agent)",
            variable=self.want_ollama,
            command=self._sync_model,
        ).pack(anchor=tk.W, pady=4)
        self.model_check = ttk.Checkbutton(
            page,
            text="Download the hermes3 model  (several GB, only if Ollama is installed)",
            variable=self.want_model,
        )
        self.model_check.pack(anchor=tk.W, pady=4)
        ttk.Checkbutton(page, text="Desktop shortcut", variable=self.want_desktop).pack(anchor=tk.W, pady=(12, 4))
        ttk.Checkbutton(page, text="Start menu shortcut", variable=self.want_start).pack(anchor=tk.W, pady=4)
        return page

    def _progress(self):
        page = ttk.Frame(self.body)
        ttk.Label(page, text="Installing", font=("Segoe UI", 16)).pack(anchor=tk.W, pady=(0, 8))
        self.progress = ttk.Progressbar(page, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 8))
        self.log = tk.Text(
            page, height=18, bg=DARK["field"], fg=DARK["fg"],
            insertbackground=DARK["fg"], relief=tk.FLAT, wrap=tk.WORD,
        )
        self.log.pack(fill=tk.BOTH, expand=True)
        return page

    def _done(self):
        page = ttk.Frame(self.body)
        ttk.Label(page, text="Setup finished", font=("Segoe UI", 16)).pack(anchor=tk.W, pady=(0, 12))
        self.done_label = ttk.Label(page, text="", justify=tk.LEFT, wraplength=680)
        self.done_label.pack(anchor=tk.W)
        ttk.Checkbutton(page, text="Launch Leftover's", variable=self.launch_after).pack(anchor=tk.W, pady=16)
        return page

    def show_page(self, index):
        for page in self.pages:
            page.pack_forget()
        self.page = index
        self.pages[index].pack(fill=tk.BOTH, expand=True)
        self.back_btn.configure(state="normal" if index in (1,) else "disabled")
        if index == 0:
            self.next_btn.configure(text="Next", state="normal")
            self.cancel_btn.configure(state="normal")
        elif index == 1:
            self.next_btn.configure(text="Install", state="normal" if self.payload else "disabled")
            self.cancel_btn.configure(state="normal")
        elif index == 2:
            self.next_btn.configure(text="Installing...", state="disabled")
            self.back_btn.configure(state="disabled")
            self.cancel_btn.configure(state="disabled")
        else:
            self.next_btn.configure(text="Finish", state="normal")
            self.back_btn.configure(state="disabled")
            self.cancel_btn.configure(state="disabled")

    def back(self):
        if self.page == 1:
            self.show_page(0)

    def next(self):
        if self.page == 0:
            self.show_page(1)
        elif self.page == 1:
            self.start_install()
        elif self.page == 3:
            self.finish()

    def browse(self):
        chosen = filedialog.askdirectory(initialdir=self.install_dir.get() or os.getcwd())
        if chosen:
            self.install_dir.set(chosen)

    def _sync_model(self):
        if self.want_ollama.get():
            self.model_check.state(["!disabled"])
        else:
            self.want_model.set(False)
            self.model_check.state(["disabled"])

    def write_log(self, text):
        def add():
            self.log.insert(tk.END, text + "\n")
            self.log.see(tk.END)
        self.after(0, add)

    def start_install(self):
        folder = self.install_dir.get().strip()
        if not folder:
            messagebox.showinfo("Folder", "Choose an install folder.")
            return
        if self.payload is None:
            messagebox.showerror("Missing", EXE_NAME + " was not found. Run build_exe.bat first.")
            return
        self.show_page(2)
        self.progress.start(12)
        threading.Thread(target=self._install, args=(Path(folder),), daemon=True).start()

    def _run(self, args):
        self.write_log(" ".join(args))
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=CREATE_NO_WINDOW,
        )
        for line in proc.stdout:
            self.write_log(line.rstrip())
        proc.wait()
        return proc.returncode

    def _install(self, folder):
        ok = True
        try:
            if self.want_python.get():
                self.write_log("Installing Python 3.12...")
                code = self._run([
                    "winget", "install", "--id", "Python.Python.3.12", "-e", "--scope", "user",
                    "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity",
                ])
                if code != 0:
                    self.write_log("Python install returned " + str(code) + ". Continuing.")
            if self.want_ollama.get():
                self.write_log("Installing Ollama...")
                code = self._run([
                    "winget", "install", "--id", "Ollama.Ollama", "-e",
                    "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity",
                ])
                if code != 0:
                    self.write_log("Ollama install returned " + str(code) + ".")
                    ok = False
            folder.mkdir(parents=True, exist_ok=True)
            dest = folder / EXE_NAME
            self.write_log("Copying cleaner to " + str(dest))
            shutil.copy2(self.payload, dest)
            if self.want_desktop.get() or self.want_start.get():
                self._shortcuts(dest)
            if self.want_ollama.get() and self.want_model.get() and ok:
                self._pull_model()
            self.installed_exe = dest
        except Exception as exc:
            ok = False
            self.write_log("Setup failed: " + str(exc))
            self.installed_exe = None

        def finish_page():
            self.progress.stop()
            if ok:
                self.done_label.configure(text="Leftover's is installed.\n\n" + str(folder))
            else:
                self.done_label.configure(text="Setup finished with a problem. Read the install log if the cleaner did not appear.")
            self.show_page(3)
        self.after(0, finish_page)

    def _shortcuts(self, dest):
        desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
        start = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        targets = []
        if self.want_desktop.get():
            targets.append(desktop / "Leftover's.lnk")
        if self.want_start.get():
            targets.append(start / "Leftover's.lnk")
        ps = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        for link in targets:
            self.write_log("Shortcut: " + str(link))
            command = (
                "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('" + str(link).replace("'", "''") + "'); "
                "$s.TargetPath = '" + str(dest).replace("'", "''") + "'; "
                "$s.WorkingDirectory = '" + str(dest.parent).replace("'", "''") + "'; "
                "$s.Description = 'Leftover''s'; "
                "$s.Save()"
            )
            self._run([ps, "-NoProfile", "-Command", command])

    def _pull_model(self):
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
            Path(os.environ.get("ProgramFiles", "")) / "Ollama" / "ollama.exe",
        ]
        ollama = next((p for p in candidates if p.is_file()), None)
        if ollama is None:
            self.write_log("Ollama exe was not found yet. Open the cleaner and click Link AI to download hermes3.")
            return
        app = ollama.with_name("ollama app.exe")
        if app.is_file():
            subprocess.Popen([str(app)], creationflags=CREATE_NO_WINDOW)
        else:
            subprocess.Popen([str(ollama), "serve"], creationflags=CREATE_NO_WINDOW)
        self.write_log("Downloading hermes3. This can take a long time.")
        self._run([str(ollama), "pull", "hermes3"])

    def finish(self):
        exe = getattr(self, "installed_exe", None)
        if self.launch_after.get() and exe and Path(exe).is_file():
            subprocess.Popen([str(exe)], cwd=str(Path(exe).parent))
        self.destroy()


if __name__ == "__main__":
    if sys.platform != "win32":
        print("This setup wizard only runs on Windows.")
        sys.exit(1)
    SetupWizard().mainloop()

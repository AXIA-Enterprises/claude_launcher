#!/usr/bin/env python3
"""Claude Launcher — cross-platform folder picker.

Pick a folder from your common locations and click Open. A terminal window
opens in that folder and runs `claude --allow-dangerously-skip-permissions`.

Works on macOS, Windows, and Linux. On first launch, auto-installs the
Claude CLI via npm if missing.
"""

import json
import os
import re
import shutil
import string
import subprocess
import sys
import threading
from pathlib import Path

FAVORITES_FILE = Path.home() / ".claude_launcher_favorites.json"
STATE_FILE = Path.home() / ".claude_launcher_state.json"
RECENTS_LIMIT = 10

# --- First-run bootstrap ----------------------------------------------------
BOOTSTRAP_MARKER = Path.home() / ".claude_launcher_bootstrapped"

# .app bundles launched from Finder get a minimal PATH that excludes the
# user's shell-profile additions (nvm, pyenv, Homebrew, etc.). Query the
# login shell for its real PATH and merge it in — this picks up whatever
# `claude` / `npm` install via, no matter the manager.
def _augment_path_from_login_shell():
    shell = os.environ.get("SHELL", "/bin/bash")
    try:
        r = subprocess.run([shell, "-l", "-c", "echo $PATH"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            user_path = r.stdout.strip()
            existing = os.environ.get("PATH", "")
            # Prepend user path so their tools win over system ones.
            os.environ["PATH"] = (user_path + os.pathsep + existing
                                  if existing else user_path)
    except Exception:
        pass


# Static fallbacks in case the login-shell trick fails.
_EXTRA_PATHS = [
    "/opt/homebrew/bin", "/opt/homebrew/sbin",
    "/usr/local/bin", "/usr/local/sbin",
    str(Path.home() / ".local" / "bin"),
    str(Path.home() / ".npm-global" / "bin"),
    str(Path.home() / "bin"),
]


def _setup_path():
    if sys.platform == "darwin" or sys.platform.startswith("linux"):
        _augment_path_from_login_shell()
    existing = os.environ.get("PATH", "").split(os.pathsep)
    merged = existing + [p for p in _EXTRA_PATHS if p not in existing]
    os.environ["PATH"] = os.pathsep.join([p for p in merged if p])


_setup_path()


def _run(cmd, **kw):
    return subprocess.run(cmd, check=False, **kw)


def _gui_alert(title, message):
    """Best-effort cross-platform alert without requiring tkinter."""
    if sys.platform == "darwin":
        _run(["osascript", "-e",
              f'display alert "{title}" message "{message}"'])
    elif sys.platform == "win32":
        _run(["powershell", "-Command",
              f"[System.Windows.Forms.MessageBox]::Show('{message}','{title}')"])
    else:
        print(f"[{title}] {message}", file=sys.stderr)


def _ensure_tkinter():
    """Try-import tkinter. On Linux, python3-tk is often separate."""
    try:
        import tkinter  # noqa: F401
        return
    except ImportError:
        pass
    if sys.platform not in ("linux", "linux2"):
        _gui_alert("Claude Launcher",
                   "tkinter is missing. Reinstall Python 3 from python.org.")
        sys.exit(1)
    for pm, install in [
        ("apt-get", ["sudo", "apt-get", "install", "-y", "python3-tk"]),
        ("dnf", ["sudo", "dnf", "install", "-y", "python3-tkinter"]),
        ("pacman", ["sudo", "pacman", "-S", "--noconfirm", "tk"]),
    ]:
        if shutil.which(pm):
            _run(install)
            break
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("Install python3-tk via your package manager.", file=sys.stderr)
        sys.exit(1)


def _ensure_claude_cli():
    """If `claude` is missing, try to install via npm silently."""
    if shutil.which("claude") is not None:
        return
    npm = shutil.which("npm")
    if not npm:
        _gui_alert(
            "Claude CLI missing",
            "The Claude CLI is not installed and npm was not found. "
            "Install Node.js from nodejs.org, then run: "
            "npm install -g @anthropic-ai/claude-code"
        )
        return
    _run([npm, "install", "-g", "@anthropic-ai/claude-code"],
         capture_output=True, text=True)


def _bootstrap():
    _ensure_tkinter()
    if BOOTSTRAP_MARKER.exists():
        return
    _ensure_claude_cli()
    try:
        BOOTSTRAP_MARKER.touch()
    except OSError:
        pass


_bootstrap()

import tkinter as tk  # noqa: E402
from tkinter import messagebox, simpledialog, ttk  # noqa: E402

# The shell one-liner the launcher hands to the platform's terminal.
#
# On Unix (macOS / Linux) we bump the per-shell file-descriptor limit
# first — the default 256 is too low and triggers "low max file
# descriptors" warnings from claude. The `ulimit` failure path is silenced
# (system hard limit varies), and claude still launches.
#
# `cmd.exe` on Windows has no `ulimit` and no equivalent that claude
# needs, and POSIX redirection (`2>/dev/null`) and `;` separators don't
# parse correctly there. Use a clean Windows-friendly command instead.
if sys.platform == "win32":
    CLAUDE_CMD = "claude --allow-dangerously-skip-permissions"
else:
    CLAUDE_CMD = (
        "ulimit -n 65536 2>/dev/null; "
        "claude --allow-dangerously-skip-permissions"
    )

# Palette — dark mode (charcoal / soft white / accent blue)
BG = "#1E1F24"
PANEL = "#26282E"
ACCENT = "#4BA3E3"
ACCENT_HOVER = "#62B6EE"
TEXT = "#E8EAED"
MUTED = "#8A99A8"
BORDER = "#3A3D44"


def get_roots():
    """Return a list of (label, Path) for common locations on this OS."""
    home = Path.home()
    roots = []

    def add(label, p):
        if p.exists() and p.is_dir():
            roots.append((label, p))

    if sys.platform == "darwin":
        add("Desktop", home / "Desktop")
        add("Documents", home / "Documents")
        add("Downloads", home / "Downloads")
        add("Home", home)
        add("Developer", home / "Developer")
        add("Projects", home / "Projects")
        volumes = Path("/Volumes")
        if volumes.exists():
            for v in sorted(volumes.iterdir()):
                if v.is_dir():
                    roots.append((f"Drive: {v.name}", v))
    elif sys.platform == "win32":
        # On Windows with OneDrive folder redirection, Desktop/Documents live
        # under %OneDrive% rather than %USERPROFILE%. Prefer the redirected
        # location when it exists, otherwise fall back to the home-dir version.
        onedrive = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
        onedrive_path = Path(onedrive) if onedrive else None

        def add_win(label, name):
            if onedrive_path is not None:
                redirected = onedrive_path / name
                if redirected.exists() and redirected.is_dir():
                    roots.append((label, redirected))
                    return
            add(label, home / name)

        add_win("Desktop", "Desktop")
        add_win("Documents", "Documents")
        add("Downloads", home / "Downloads")
        add("Home", home)
        for letter in string.ascii_uppercase:
            d = Path(f"{letter}:\\")
            if d.exists():
                roots.append((f"Drive: {letter}:", d))
    else:
        add("Desktop", home / "Desktop")
        add("Documents", home / "Documents")
        add("Downloads", home / "Downloads")
        add("Home", home)
        for base in (Path("/mnt"), Path("/media")):
            if base.exists():
                for v in sorted(base.iterdir()):
                    if v.is_dir():
                        roots.append((f"Mount: {v.name}", v))
    return roots


_GIT_URL_RE = re.compile(
    r"^("
    r"https?://[^\s]+?(?:\.git)?/?"        # https://host/owner/repo[.git]
    r"|git@[^\s:]+:[^\s]+?(?:\.git)?/?"    # git@host:owner/repo[.git]
    r"|ssh://git@[^\s]+?(?:\.git)?/?"      # ssh://git@host/owner/repo[.git]
    r")$"
)


def _looks_like_git_url(s: str) -> bool:
    if not s:
        return False
    return bool(_GIT_URL_RE.match(s.strip()))


def _repo_name_from_url(url: str) -> str | None:
    """Extract the repo name (last path segment, no .git) from a git URL."""
    s = url.strip().rstrip("/")
    if s.endswith(".git"):
        s = s[:-4]
    # Handle git@host:owner/repo and ssh/https URLs alike.
    s = s.replace(":", "/")
    name = s.rsplit("/", 1)[-1]
    return name or None


def _shell_single_quote(s: str) -> str:
    """POSIX-safe single-quoting for a shell argument."""
    return "'" + s.replace("'", "'\\''") + "'"


def launch_terminal(directory: Path):
    d = str(directory)

    if sys.platform == "darwin":
        shell_cmd = f"cd {_shell_single_quote(d)} && {CLAUDE_CMD}"
        script = (
            'tell application "Terminal"\n'
            f'  do script "{shell_cmd}"\n'
            "  activate\n"
            "end tell"
        )
        subprocess.run(["osascript", "-e", script], check=False)

    elif sys.platform == "win32":
        subprocess.Popen(
            ["cmd", "/c", "start", "Claude Launcher", "cmd", "/k",
             f'cd /d "{d}" && {CLAUDE_CMD}']
        )

    else:
        terminals = [
            ("gnome-terminal",
             lambda: ["gnome-terminal", f"--working-directory={d}", "--",
                      "bash", "-c", f"{CLAUDE_CMD}; exec bash"]),
            ("konsole",
             lambda: ["konsole", "--workdir", d, "-e",
                      "bash", "-c", f"{CLAUDE_CMD}; exec bash"]),
            ("xfce4-terminal",
             lambda: ["xfce4-terminal", f"--working-directory={d}",
                      "-e", f"bash -c '{CLAUDE_CMD}; exec bash'"]),
            ("xterm",
             lambda: ["xterm", "-e",
                      f"bash -c 'cd \"{d}\" && {CLAUDE_CMD}; exec bash'"]),
        ]
        for name, build in terminals:
            if shutil.which(name):
                subprocess.Popen(build())
                return
        raise RuntimeError(
            "No supported terminal emulator found. Install gnome-terminal, "
            "konsole, xfce4-terminal, or xterm."
        )


def reveal_in_file_manager(path: Path):
    """Cross-platform 'show in folder' for a path."""
    p = str(path)
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", p], check=False)
    elif sys.platform == "win32":
        subprocess.run(["explorer", "/select,", p], check=False)
    else:
        subprocess.run(["xdg-open", str(path.parent)], check=False)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Claude Launcher")
        self.minsize(900, 580)
        self.configure(bg=BG)

        self._node_paths: dict[str, Path] = {}
        self._favorites: list[Path] = self._load_favorites()
        self._enter_primed_node: str | None = None

        # State (recents + window geometry).
        state = self._load_state()
        self._recents: list[Path] = [Path(p) for p in state.get("recents", [])
                                      if isinstance(p, str)]
        geom = state.get("geometry")
        self.geometry(geom if isinstance(geom, str) else "920x880")

        self._style()
        self._build()
        self._populate_roots()
        self._bind_shortcuts()

        # Persist geometry + recents on close.
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    @staticmethod
    def _load_state() -> dict:
        try:
            return json.loads(STATE_FILE.read_text())
        except (OSError, ValueError):
            return {}

    def _save_state(self):
        try:
            STATE_FILE.write_text(json.dumps({
                "recents": [str(p) for p in self._recents],
                "geometry": self.geometry(),
            }, indent=2))
        except OSError:
            pass

    def _on_close(self):
        self._save_state()
        self.destroy()

    def _add_to_recents(self, path: Path):
        """Move `path` to the top of recents, dedup, cap to limit."""
        try:
            path = path.resolve()
        except OSError:
            pass
        self._recents = [p for p in self._recents if p != path]
        self._recents.insert(0, path)
        self._recents = self._recents[:RECENTS_LIMIT]
        self._save_state()

    @staticmethod
    def _load_favorites() -> list[Path]:
        try:
            data = json.loads(FAVORITES_FILE.read_text())
            return [Path(p) for p in data if isinstance(p, str)]
        except (OSError, ValueError):
            return []

    def _save_favorites(self):
        try:
            FAVORITES_FILE.write_text(
                json.dumps([str(p) for p in self._favorites], indent=2))
        except OSError:
            pass

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Header.TLabel", background=BG, foreground=TEXT,
                        font=("Helvetica", 26, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground=MUTED,
                        font=("Helvetica", 13))
        style.configure("Path.TLabel", background=PANEL, foreground=TEXT,
                        font=("Helvetica", 13), padding=13)
        style.configure("Treeview", background=BG, foreground=TEXT,
                        fieldbackground=BG, borderwidth=0, rowheight=36,
                        font=("Helvetica", 14))
        style.layout("Treeview", [
            ("Treeview.treearea", {"sticky": "nswe"})
        ])
        style.map("Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])
        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                        font=("Helvetica", 14, "bold"),
                        padding=(26, 13), borderwidth=0, focuscolor=ACCENT)
        style.map("Accent.TButton",
                  background=[("disabled", BORDER),
                              ("active", ACCENT_HOVER),
                              ("!active", ACCENT)],
                  foreground=[("disabled", MUTED)])
        style.configure("Ghost.TButton", background=PANEL, foreground=TEXT,
                        font=("Helvetica", 13),
                        padding=(21, 12), borderwidth=0, focuscolor=PANEL)
        style.map("Ghost.TButton",
                  background=[("active", BORDER)])
        style.configure("Vertical.TScrollbar", background=PANEL,
                        troughcolor=BG, borderwidth=0, arrowcolor=MUTED)

    def _build(self):
        pad = 23

        header = ttk.Frame(self)
        header.pack(fill="x", padx=pad, pady=(pad, 4))
        ttk.Label(header, text="Claude Launcher",
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(header,
                  text="Pick a folder — a terminal opens with Claude running.",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 0))

        wrap = tk.Frame(self, bg=BORDER, highlightthickness=1,
                        highlightbackground=BORDER, bd=0)
        wrap.pack(fill="both", expand=True, padx=pad, pady=10)

        self.tree = ttk.Treeview(wrap, show="tree", selectmode="browse")
        vsb = ttk.Scrollbar(wrap, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewOpen>>", self._on_expand)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda _e: self._open())
        self.tree.bind("<Return>", self._on_enter)
        self.tree.bind("<KP_Enter>", self._on_enter)

        # Slow down trackpad/mousewheel scrolling. Default macOS scrolls
        # ~event.delta rows per event, which feels frantic on a trackpad.
        # We accumulate deltas and only step a row when the threshold is
        # crossed — bigger threshold = slower scroll.
        self._scroll_accum = 0.0
        self._scroll_threshold = 7.0  # raise to slow further, lower to speed up

        def _on_wheel(event):
            # event.delta sign: + = up, - = down on macOS/Windows
            self._scroll_accum += event.delta
            steps = int(self._scroll_accum / self._scroll_threshold)
            if steps != 0:
                self.tree.yview_scroll(-steps, "units")
                self._scroll_accum -= steps * self._scroll_threshold
            return "break"

        # macOS / Windows
        self.tree.bind("<MouseWheel>", _on_wheel)
        # Linux uses Button-4 / Button-5 instead of MouseWheel.
        self.tree.bind("<Button-4>",
                       lambda _e: (self.tree.yview_scroll(-1, "units"), "break"))
        self.tree.bind("<Button-5>",
                       lambda _e: (self.tree.yview_scroll(1, "units"), "break"))

        self.path_var = tk.StringVar(value="No folder selected")
        ttk.Label(self, textvariable=self.path_var,
                  style="Path.TLabel").pack(fill="x", padx=pad, pady=(0, 10))

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=pad, pady=(0, pad))
        ttk.Button(btns, text="Refresh", style="Ghost.TButton",
                   command=self._refresh).pack(side="left")
        ttk.Button(btns, text="New Folder", style="Ghost.TButton",
                   command=self._new_folder).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Clone Repo", style="Ghost.TButton",
                   command=self._clone_repo).pack(side="left", padx=(8, 0))
        self.pin_btn = ttk.Button(btns, text="★ Pin", style="Ghost.TButton",
                                   command=self._toggle_pin, state="disabled")
        self.pin_btn.pack(side="left", padx=(8, 0))
        self.open_btn = ttk.Button(btns, text="Open in Terminal",
                                   style="Accent.TButton",
                                   command=self._open, state="disabled")
        self.open_btn.pack(side="right")

    def _populate_roots(self):
        # Recents group at the very top.
        live_recents = [p for p in self._recents if p.exists() and p.is_dir()]
        if live_recents:
            recents_root = self.tree.insert("", "end",
                                             text="  ⏱ Recents", open=True)
            for r in live_recents:
                node = self.tree.insert(recents_root, "end",
                                         text=f"  {r.name or r}", open=False)
                self._node_paths[node] = r
                if self._has_subdirs(r):
                    self.tree.insert(node, "end", text="…")

        # Pinned group — only if any favorites exist.
        if self._favorites:
            pinned_root = self.tree.insert("", "end",
                                            text="  ★ Pinned", open=True)
            for fav in self._favorites:
                if fav.exists() and fav.is_dir():
                    node = self.tree.insert(pinned_root, "end",
                                             text=f"  {fav.name or fav}",
                                             open=False)
                    self._node_paths[node] = fav
                    if self._has_subdirs(fav):
                        self.tree.insert(node, "end", text="…")

        for label, path in get_roots():
            node = self.tree.insert("", "end", text=f"  {label}", open=False)
            self._node_paths[node] = path
            if self._has_subdirs(path):
                self.tree.insert(node, "end", text="…")

    def _bind_shortcuts(self):
        """Standard Mac (Cmd) / cross-platform (Ctrl) keyboard shortcuts."""
        mod = "Command" if sys.platform == "darwin" else "Control"
        self.bind_all(f"<{mod}-w>", lambda _e: self._on_close())
        self.bind_all(f"<{mod}-q>", lambda _e: self._on_close())
        self.bind_all(f"<{mod}-n>", lambda _e: self._new_folder())
        self.bind_all(f"<{mod}-Shift-N>", lambda _e: self._clone_repo())
        self.bind_all(f"<{mod}-r>", lambda _e: self._refresh())
        # Esc clears selection / disarms Enter prime.
        self.bind_all("<Escape>", lambda _e: self._clear_selection())

        # Right-click context menu. Mac uses Button-2 for two-finger /
        # control-click; Linux/Windows use Button-3.
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Button-2>", self._show_context_menu)
        self.tree.bind("<Control-Button-1>", self._show_context_menu)

    def _clear_selection(self):
        for n in self.tree.selection():
            self.tree.selection_remove(n)
        self._enter_primed_node = None
        self._on_select(None)

    def _show_context_menu(self, event):
        # Identify the row under the pointer and select it.
        row = self.tree.identify_row(event.y)
        if not row or row not in self._node_paths:
            return
        self.tree.selection_set(row)
        self.tree.focus(row)
        path = self._node_paths[row]

        menu = tk.Menu(self, tearoff=0,
                       bg=PANEL, fg=TEXT,
                       activebackground=ACCENT, activeforeground="white",
                       borderwidth=0)
        menu.add_command(label="Open in Terminal",
                         command=lambda: self._open_path(path))
        menu.add_command(label="Reveal in Finder",
                         command=lambda: reveal_in_file_manager(path))
        menu.add_command(label="Copy Path",
                         command=lambda: self._copy_path(path))
        menu.add_separator()
        pinned = path in self._favorites
        menu.add_command(label="Unpin" if pinned else "Pin",
                         command=self._toggle_pin)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy_path(self, path: Path):
        self.clipboard_clear()
        self.clipboard_append(str(path))

    def _open_path(self, path: Path):
        """Open a specific path with Claude (used by context menu / shortcuts)."""
        try:
            launch_terminal(path)
            self._add_to_recents(path)
        except Exception as exc:
            messagebox.showerror("Could not open terminal", str(exc))

    def _on_enter(self, _event):
        node = self.tree.focus()
        if not node or node not in self._node_paths:
            return "break"
        if self._enter_primed_node == node:
            self._enter_primed_node = None
            self._open()
            return "break"
        self._enter_primed_node = node
        path = self._node_paths[node]
        self.path_var.set(f"↵ Press Enter again to open: {path}")
        return "break"

    def _toggle_pin(self):
        node = self.tree.focus()
        path = self._node_paths.get(node)
        if not path:
            return
        if path in self._favorites:
            self._favorites.remove(path)
        else:
            self._favorites.append(path)
        self._save_favorites()
        self._refresh()

    @staticmethod
    def _has_subdirs(path: Path) -> bool:
        try:
            for p in path.iterdir():
                if p.is_dir() and not p.name.startswith("."):
                    return True
        except (PermissionError, OSError):
            pass
        return False

    def _on_expand(self, _event):
        node = self.tree.focus()
        if not node:
            return
        children = self.tree.get_children(node)
        if len(children) == 1 and self.tree.item(children[0], "text") == "…":
            self.tree.delete(children[0])
            self._load_children(node, self._node_paths[node])

    def _load_children(self, parent_node, path: Path):
        try:
            entries = sorted(
                (p for p in path.iterdir()
                 if p.is_dir() and not p.name.startswith(".")),
                key=lambda p: p.name.lower(),
            )
        except (PermissionError, OSError):
            return
        for p in entries:
            child = self.tree.insert(parent_node, "end",
                                     text=f"  {p.name}", open=False)
            self._node_paths[child] = p
            if self._has_subdirs(p):
                self.tree.insert(child, "end", text="…")

    def _on_select(self, _event):
        # Selection changed — disarm any pending Enter.
        self._enter_primed_node = None
        node = self.tree.focus()
        path = self._node_paths.get(node)
        if path:
            self.path_var.set(str(path))
            self.open_btn.configure(state="normal")
            self.pin_btn.configure(
                state="normal",
                text="★ Unpin" if path in self._favorites else "★ Pin",
            )
        else:
            self.path_var.set("No folder selected")
            self.open_btn.configure(state="disabled")
            self.pin_btn.configure(state="disabled", text="★ Pin")

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        self._node_paths.clear()
        self._enter_primed_node = None
        self.path_var.set("No folder selected")
        self.open_btn.configure(state="disabled")
        self.pin_btn.configure(state="disabled", text="★ Pin")
        self._populate_roots()

    def _new_folder(self):
        node = self.tree.focus()
        parent_path = self._node_paths.get(node) or (Path.home() / "Desktop")
        if not parent_path.is_dir():
            messagebox.showerror("Invalid location",
                                 f"{parent_path} is not a folder.")
            return

        name = simpledialog.askstring(
            "New Folder",
            f"Create new folder inside:\n{parent_path}\n\nName:",
            parent=self,
        )
        if not name:
            return
        name = name.strip()
        if not name or any(c in name for c in '/\\:*?"<>|'):
            messagebox.showerror("Invalid name",
                                 "Folder name contains invalid characters.")
            return

        new_path = parent_path / name
        try:
            new_path.mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            messagebox.showerror("Already exists",
                                 f"A folder named '{name}' already exists here.")
            return
        except OSError as exc:
            messagebox.showerror("Could not create folder", str(exc))
            return

        if node and self.tree.item(node, "open"):
            new_node = self.tree.insert(node, "end",
                                        text=f"  {name}", open=False)
            self._node_paths[new_node] = new_path
            self.tree.selection_set(new_node)
            self.tree.focus(new_node)
            self.tree.see(new_node)
        else:
            self.path_var.set(str(new_path))
            self.open_btn.configure(state="normal")

        try:
            launch_terminal(new_path)
            self._add_to_recents(new_path)
        except Exception as exc:
            messagebox.showerror("Could not open terminal", str(exc))

    # --- Clone repo flow ----------------------------------------------------

    def _clone_repo(self):
        # Pre-fill URL from clipboard if it looks like a git URL.
        prefill = ""
        try:
            clip = self.clipboard_get()
            if _looks_like_git_url(clip):
                prefill = clip.strip()
        except tk.TclError:
            pass

        url = simpledialog.askstring(
            "Clone Repo",
            "Git repo URL (https://github.com/owner/repo or git@host:owner/repo):",
            initialvalue=prefill,
            parent=self,
        )
        if not url:
            return
        url = url.strip()
        if not _looks_like_git_url(url):
            messagebox.showerror("Invalid URL",
                                 "That doesn't look like a git repo URL.")
            return

        repo_name = _repo_name_from_url(url)
        if not repo_name:
            messagebox.showerror("Invalid URL",
                                 "Could not determine a repo name from that URL.")
            return

        # Destination parent: selected folder, or ~/Documents fallback.
        node = self.tree.focus()
        parent_path = self._node_paths.get(node)
        if not parent_path or not parent_path.is_dir():
            parent_path = Path.home() / "Documents"
            parent_path.mkdir(exist_ok=True)

        target = parent_path / repo_name

        # Conflict resolution.
        if target.exists():
            choice = self._ask_conflict(repo_name, target)
            if choice is None:
                return  # cancel
            if choice == "overwrite":
                try:
                    shutil.rmtree(target)
                except OSError as exc:
                    messagebox.showerror("Could not overwrite",
                                         f"Failed to remove {target}: {exc}")
                    return
            elif choice == "rename":
                new_name = simpledialog.askstring(
                    "Rename clone",
                    f"Folder '{repo_name}' exists in {parent_path}.\n"
                    f"Choose a new folder name:",
                    initialvalue=repo_name + "-2",
                    parent=self,
                )
                if not new_name:
                    return
                new_name = new_name.strip()
                if not new_name or any(c in new_name for c in '/\\:*?"<>|'):
                    messagebox.showerror("Invalid name",
                                         "Folder name contains invalid characters.")
                    return
                target = parent_path / new_name
                if target.exists():
                    messagebox.showerror("Already exists",
                                         f"'{new_name}' also exists. Aborting.")
                    return

        if not shutil.which("git"):
            messagebox.showerror(
                "git not found",
                "The `git` command is not available on PATH. "
                "Install Xcode Command Line Tools or `brew install git`."
            )
            return

        self._run_clone_with_progress(url, target)

    def _ask_conflict(self, name: str, target: Path) -> str | None:
        """Modal asking Overwrite / Rename / Cancel. Returns 'overwrite',
        'rename', or None for cancel."""
        dlg = tk.Toplevel(self)
        dlg.title("Folder already exists")
        dlg.configure(bg=BG)
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)

        ttk.Label(
            dlg,
            text=f"A folder named '{name}' already exists in:\n{target.parent}",
            style="Sub.TLabel",
            justify="left",
        ).pack(padx=24, pady=(20, 14), anchor="w")

        result = {"choice": None}

        def pick(choice):
            result["choice"] = choice
            dlg.destroy()

        btns = ttk.Frame(dlg)
        btns.pack(padx=24, pady=(0, 20), fill="x")
        ttk.Button(btns, text="Cancel", style="Ghost.TButton",
                   command=lambda: pick(None)).pack(side="left")
        ttk.Button(btns, text="Rename", style="Ghost.TButton",
                   command=lambda: pick("rename")).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Overwrite", style="Accent.TButton",
                   command=lambda: pick("overwrite")).pack(side="right")

        dlg.update_idletasks()
        # Center over parent
        x = self.winfo_rootx() + (self.winfo_width() - dlg.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dlg.winfo_height()) // 3
        dlg.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        self.wait_window(dlg)
        return result["choice"]

    def _run_clone_with_progress(self, url: str, target: Path):
        """Run `git clone` in a background thread; show modal spinner."""
        progress = tk.Toplevel(self)
        progress.title("Cloning…")
        progress.configure(bg=BG)
        progress.transient(self)
        progress.grab_set()
        progress.resizable(False, False)
        progress.protocol("WM_DELETE_WINDOW", lambda: None)  # disable close

        ttk.Label(progress, text="Cloning repository…",
                  style="Header.TLabel").pack(padx=32, pady=(24, 8), anchor="w")
        ttk.Label(progress, text=f"{url}\n→ {target}",
                  style="Sub.TLabel", justify="left",
                  wraplength=560).pack(padx=32, pady=(0, 12), anchor="w")
        bar = ttk.Progressbar(progress, mode="indeterminate", length=520)
        bar.pack(padx=32, pady=(0, 24))
        bar.start(10)

        progress.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - progress.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - progress.winfo_height()) // 3
        progress.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        result: dict = {"ok": False, "stderr": ""}

        def worker():
            try:
                proc = subprocess.run(
                    ["git", "clone", "--progress", url, str(target)],
                    capture_output=True, text=True,
                )
                result["ok"] = (proc.returncode == 0)
                result["stderr"] = proc.stderr or proc.stdout
            except Exception as exc:
                result["ok"] = False
                result["stderr"] = str(exc)
            self.after(0, lambda: self._clone_finished(progress, target, result))

        threading.Thread(target=worker, daemon=True).start()

    def _clone_finished(self, progress_dlg, target: Path, result: dict):
        try:
            progress_dlg.destroy()
        except tk.TclError:
            pass

        if not result["ok"]:
            messagebox.showerror(
                "Clone failed",
                result["stderr"].strip()[:1500] or "Unknown git error.",
            )
            return

        # Refresh tree so the new folder shows up under its parent (if visible).
        self._refresh()
        self.path_var.set(str(target))
        self.open_btn.configure(state="normal")

        try:
            launch_terminal(target)
            self._add_to_recents(target)
        except Exception as exc:
            messagebox.showerror("Could not open terminal", str(exc))

    def _open(self):
        node = self.tree.focus()
        path = self._node_paths.get(node)
        if not path:
            return
        try:
            launch_terminal(path)
            self._add_to_recents(path)
        except Exception as exc:
            messagebox.showerror("Could not open terminal", str(exc))


if __name__ == "__main__":
    App().mainloop()

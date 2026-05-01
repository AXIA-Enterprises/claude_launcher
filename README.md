# Claude Launcher

A free, cross-platform desktop application that makes starting a Claude Code
session a single click. It is built and provided by **AXIA Enterprises** and
released as open source under the MIT license.

## What it does

Claude Launcher is a small graphical folder picker. The user selects a folder
from a list of common locations (Desktop, Documents, Downloads, mounted
drives, pinned favorites, recents) and clicks **Open in Terminal**. The
application then opens the platform's native terminal at that folder and runs
the [Claude CLI](https://github.com/anthropics/claude-code) in
`--allow-dangerously-skip-permissions` mode.

It removes the manual ritual of opening a terminal, navigating to a project,
and starting Claude — those steps collapse into one click.

The application also offers:

- **Recents** — the most recently opened folders are listed at the top
- **Pinned favorites** — frequently used folders can be pinned for one-click access
- **New Folder** — create a new folder and immediately start Claude in it
- **Clone Repo** — paste a Git URL and clone it into the selected folder, then start Claude
- **Right-click menu** — open in terminal, reveal in file manager, copy path, pin/unpin
- **Keyboard shortcuts** — standard ⌘/Ctrl bindings for new, refresh, quit
- **Dark theme** — easy on the eyes

The application is intentionally small. It does one thing well and otherwise
stays out of the way.

## Pricing

Claude Launcher is **free of charge** and will remain so. There are no paid
tiers, no in-app purchases, no donations, and no advertising. The source is
public and contributions are welcome.

## Privacy

Claude Launcher **does not collect, transmit, or store any user data**. There
is no telemetry, no analytics, no crash reporting, no account system, and no
network communication initiated by the application itself.

Two minor exceptions, both initiated by the user:

1. **First-run bootstrap** — if the Claude CLI is not already installed, the
   application runs `npm install -g @anthropic-ai/claude-code` once. This
   contacts the public npm registry. After the first successful run, this is
   never repeated.
2. **Clone Repo** — if the user clicks Clone Repo and provides a Git URL,
   the application invokes `git clone` against that URL.

Both actions are local subprocess invocations of standard developer tooling
(`npm`, `git`); the launcher does not proxy, observe, or store the data
involved.

The Claude CLI launched inside the terminal is a separate product by Anthropic
with its own privacy practices. Refer to Anthropic's documentation for
details on what the Claude CLI itself sends.

For full details, see [PRIVACY.md](PRIVACY.md).

## Supported platforms

| Platform | Terminal used |
|---|---|
| macOS | Terminal.app (via `osascript`) |
| Windows | `cmd.exe` (`cmd /k`) |
| Linux | first available of `gnome-terminal`, `konsole`, `xfce4-terminal`, `xterm` |

## Requirements

- **Python 3.10 or newer** with Tkinter included. Tkinter ships with the
  python.org installers on macOS and Windows. On Linux it is typically a
  separate package (`python3-tk` on Debian/Ubuntu, `python3-tkinter` on
  Fedora). The application attempts to install it automatically on first run.
- **Node.js / `npm`** — only required if the Claude CLI is not already
  installed. The application will perform a one-time global install via npm.
- **Git** — only required for the Clone Repo feature.

## Installation

```bash
git clone https://github.com/AXIA-Enterprises/claude_launcher.git
cd claude_launcher
python3 claude_launcher.py
```

That is the entire installation process. The application has zero third-party
Python dependencies at runtime.

## Optional: building a macOS application bundle

A helper script generates a polished icon for use when packaging the launcher
into a `.app` bundle. The icon script depends on Pillow:

```bash
pip install -r requirements.txt
python3 make_icon.py
```

The output is `AppIcon.icns` next to the script. From there, any standard
packaging tool ([py2app](https://py2app.readthedocs.io/),
[Platypus](https://sveinbjorn.org/platypus), or a hand-rolled `Info.plist`)
can be used to produce a distributable `.app`.

## Local files written by the application

The application writes three small files to the user's home directory:

| File | Purpose |
|---|---|
| `~/.claude_launcher_favorites.json` | Pinned folders |
| `~/.claude_launcher_state.json` | Recents list and last window geometry |
| `~/.claude_launcher_bootstrapped` | Marker indicating first-run setup completed |

Deleting any of these resets the corresponding piece of local state. The
files are plain JSON (or empty) and can be inspected at any time. They never
leave the user's machine.

## How it works

The application is a single Python script (`claude_launcher.py`) built on
Tkinter. When the user selects a folder and clicks Open, it constructs a
shell one-liner of the form:

```sh
ulimit -n 65536 2>/dev/null; claude --allow-dangerously-skip-permissions
```

and asks the operating system's terminal emulator to run it in the chosen
directory.

On macOS, application bundles launched from Finder receive a stripped-down
`PATH` from launchd that omits the user's shell-profile additions (nvm,
pyenv, Homebrew, and similar). On startup, the launcher queries the user's
login shell for its real `PATH` and merges it into the process environment,
so `claude` and `npm` are resolved correctly regardless of how they were
installed.

## Development

```bash
# Smoke test (verifies both source files compile cleanly)
python3 -m pytest tests/

# Lint
ruff check .
```

There are no full GUI tests. Tkinter is awkward to drive headlessly, and the
launcher is small enough that visual verification on each platform is the
practical choice. The test suite exists as a compile floor for CI; meaningful
behavior verification is done manually.

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md)
for development guidelines. For security-relevant reports, see
[SECURITY.md](SECURITY.md).

## License

Released under the [MIT license](LICENSE). Copyright © 2026 Claude Launcher
contributors.

---

*Built and provided by **AXIA Enterprises**.*

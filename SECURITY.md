# Security

Claude Launcher is a thin wrapper that opens a terminal and runs the Claude
CLI. It does not handle credentials, store secrets, or talk to the network on
its own. The project is built and provided by **AXIA Enterprises** under the
MIT License.

## Reporting a vulnerability

If a security issue is found, please **do not** open a public issue. Open a
private security advisory on the repository (GitHub → Security → Advisories
→ "Report a vulnerability"), or contact the maintainers at the address
listed on the repository's GitHub profile.

The maintainers will acknowledge within a few days and aim to resolve in
coordination with the reporter.

## Scope

**In scope:**
- Issues in `claude_launcher.py` or `make_icon.py` that allow code execution,
  privilege escalation, or unintended filesystem access on the user's machine.
- Issues in the clone-repo flow (e.g. shell-injection via crafted URLs).

**Out of scope:**
- Vulnerabilities in the Claude CLI itself — those should be reported upstream at
  https://github.com/anthropics/claude-code.
- Vulnerabilities in `tkinter`, Python itself, `git`, `npm`, or the OS
  terminal emulator. Those should be reported to the relevant upstream
  project.

## A note on `--allow-dangerously-skip-permissions`

The launcher exists to make it convenient to start Claude in
"dangerously-skip-permissions" mode. That mode allows Claude to read and write
any file in the launched directory without prompting. **This is intentional
and is the entire purpose of the application.** The launcher should only be
pointed at directories whose contents the user is comfortable letting an AI
modify autonomously.

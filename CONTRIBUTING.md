# Contributing

Thanks for considering a contribution.

## Quick start

```bash
git clone https://github.com/<your-fork>/claude_launcher.git
cd claude_launcher
python3 claude_launcher.py    # run the app
python3 -m pytest tests/      # run smoke tests
```

The app has zero runtime third-party dependencies. The only optional
dependency is Pillow, used by `make_icon.py` to generate the macOS `.icns`
icon — `pip install -r requirements.txt` covers that.

## Style

- Standard library only for the runtime path. If you need a third-party
  package for a runtime feature, please open an issue first to discuss — the
  zero-dependency property is intentional.
- 4-space indents, PEP 8.
- Keep `claude_launcher.py` runnable as a single file. Multi-module
  refactors are fine if motivated, but coordinate via an issue first.

## Pull requests

- Open against `main`.
- Include a short description of what changed and why.
- Tests welcome but not required for tkinter-only changes (see
  `tests/test_smoke.py` for the bar — at minimum, the file should still
  compile and the app should still launch).
- One change per PR. If you find unrelated cleanup along the way, please
  split it into a separate PR.

## Reporting bugs

File a GitHub issue with:
- OS + version
- Python version (`python3 --version`)
- What you did, what happened, what you expected
- Any traceback or error dialog text

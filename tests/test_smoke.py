"""Smoke tests — verify both source files compile cleanly.

Tkinter GUI code is hard to test headlessly, and the launcher is a single
~900-line script that's better validated by visual inspection. This file
exists as a CI floor: if either script stops parsing, CI fails.
"""

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_launcher_compiles():
    py_compile.compile(str(ROOT / "claude_launcher.py"), doraise=True)


def test_make_icon_compiles():
    py_compile.compile(str(ROOT / "make_icon.py"), doraise=True)

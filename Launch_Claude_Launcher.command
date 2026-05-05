#!/bin/bash
# Double-clickable launcher for macOS Finder.
#
# How to use:
#   - Open Finder, navigate to the claude_launcher folder
#   - Double-click this file
#   - A Terminal window opens briefly and Claude Launcher starts
#
# To use as a Desktop shortcut: download the prebuilt ClaudeLauncher.app
# from the GitHub release page and drag it to your Desktop instead.
# (.command files copied to the Desktop won't know where the source code
# lives; the .app is self-contained.)

cd "$(dirname "$0")"
exec python3 claude_launcher.py

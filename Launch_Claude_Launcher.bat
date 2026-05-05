@echo off
REM Double-clickable launcher for Windows.
REM
REM How to use:
REM   - Navigate to the claude_launcher folder in Explorer
REM   - Double-click this file
REM   - A console window opens briefly and Claude Launcher starts
REM
REM To use as a Desktop shortcut: right-click this file in the repo
REM folder, choose "Create shortcut", then drag the shortcut to your
REM Desktop. The shortcut will continue to launch from the repo location.

cd /d "%~dp0"
python claude_launcher.py

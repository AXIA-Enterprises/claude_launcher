#!/usr/bin/env bash
# Build ClaudeLauncher.app — a hand-rolled, ad-hoc-signed macOS app bundle.
#
# Requires: macOS, Python 3.10+ with tkinter, and Pillow for icon generation
# (pip install -r requirements.txt).
#
# Output: ClaudeLauncher.app in the repo root.
# Distribution: zip with `ditto -c -k --keepParent ClaudeLauncher.app ClaudeLauncher.app.zip`

set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname)" != "Darwin" ]]; then
    echo "build_app.sh builds a macOS .app and only runs on macOS." >&2
    echo "On Windows, just double-click Launch_Claude_Launcher.bat." >&2
    echo "On Linux, run: python3 claude_launcher.py" >&2
    exit 1
fi

VERSION="${1:-0.1.0}"

# Step 1: generate the icon if missing
if [[ ! -f AppIcon.icns ]]; then
    echo "Generating AppIcon.icns..."
    python3 make_icon.py
fi

APP="ClaudeLauncher.app"
echo "Building $APP (v$VERSION)..."
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# Step 2: Info.plist
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Claude Launcher</string>
    <key>CFBundleDisplayName</key>
    <string>Claude Launcher</string>
    <key>CFBundleIdentifier</key>
    <string>com.axia-enterprises.claudelauncher</string>
    <key>CFBundleVersion</key>
    <string>${VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>ClaudeLauncher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Built and provided by AXIA Enterprises. MIT License.</string>
</dict>
</plist>
PLIST

# Step 3: PkgInfo
printf 'APPL????' > "$APP/Contents/PkgInfo"

# Step 4: launcher executable. The .app is launched by Finder via launchd,
# which provides a stripped-down PATH that excludes user shell-profile
# additions (nvm, pyenv, homebrew, python.org). Query the user's login
# shell for its real python3 location so we pick up whatever they have
# installed, regardless of the manager.
cat > "$APP/Contents/MacOS/ClaudeLauncher" <<'LAUNCHER'
#!/bin/bash
set -e
RES_DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"
SHELL_BIN="${SHELL:-/bin/zsh}"
PYTHON3="$("$SHELL_BIN" -l -c 'command -v python3' 2>/dev/null || true)"
if [ -z "$PYTHON3" ] || [ ! -x "$PYTHON3" ]; then
    PYTHON3="$(command -v python3 2>/dev/null || echo /usr/bin/python3)"
fi
exec "$PYTHON3" "$RES_DIR/claude_launcher.py"
LAUNCHER
chmod +x "$APP/Contents/MacOS/ClaudeLauncher"

# Step 5: bundle the source and icon into Resources/
cp claude_launcher.py "$APP/Contents/Resources/"
cp AppIcon.icns "$APP/Contents/Resources/"

# Step 6: ad-hoc codesign. Without this, downloaded zips of the .app are
# rejected with "is damaged and can't be opened" on modern macOS due to
# quarantine + missing signature. Ad-hoc signing turns that into the
# milder "unidentified developer" warning, which the user can bypass via
# right-click → Open the first time.
echo "Ad-hoc codesigning..."
codesign --force --deep --sign - "$APP" 2>&1 | sed 's/^/  /'

echo
echo "Built $APP successfully."
echo "  - Test locally: open $APP"
echo "  - Drag to /Applications or your Desktop"
echo "  - On first launch from a downloaded zip: right-click → Open"
echo "    (macOS shows 'unidentified developer' — this is expected for"
echo "    apps that aren't notarized through a paid Apple Developer ID.)"

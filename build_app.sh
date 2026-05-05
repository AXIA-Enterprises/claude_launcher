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
# which provides a stripped-down PATH and no controlling TTY. Spawning the
# user's login shell to query for python3 is unreliable in this context —
# user .zshrc plugins can block on read/network calls without a TTY,
# hanging the launcher indefinitely. Instead, walk a list of known
# install locations (homebrew, python.org, pyenv) and test each for
# tkinter, picking the first valid one.
cat > "$APP/Contents/MacOS/ClaudeLauncher" <<'LAUNCHER'
#!/bin/bash
RES_DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"

CANDIDATES=(
    "/opt/homebrew/bin/python3"
    "/usr/local/bin/python3"
    "$HOME/.pyenv/shims/python3"
    "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.10/bin/python3"
    "/usr/bin/python3"
)

PYTHON3=""
for c in "${CANDIDATES[@]}"; do
    if [ -x "$c" ] && "$c" -c "import tkinter" >/dev/null 2>&1; then
        PYTHON3="$c"
        break
    fi
done

if [ -z "$PYTHON3" ]; then
    osascript -e 'display alert "Claude Launcher" message "Could not find a Python 3 install with Tkinter. Install Python 3 from python.org (Tkinter is bundled) or run:\n\n  brew install python-tk@3.12"' >/dev/null 2>&1
    exit 1
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

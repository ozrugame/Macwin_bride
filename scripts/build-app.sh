#!/bin/bash
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
bash scripts/swift.sh build -c release -debug-info-format none --product MacWinBridge
binary_dir="$(bash scripts/swift.sh build -c release --show-bin-path)"
app="$project_dir/dist/MacWin Bridge.app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
cp "$binary_dir/MacWinBridge" "$app/Contents/MacOS/MacWinBridge"
cat > "$app/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>MacWinBridge</string>
<key>CFBundleIdentifier</key><string>local.macwin.bridge</string>
<key>CFBundleName</key><string>MacWin Bridge</string>
<key>CFBundleDisplayName</key><string>MacWin Bridge</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>0.1.0</string>
<key>CFBundleVersion</key><string>1</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
python3 - "$project_dir" "$app/Contents/Resources/project.json" <<'PY'
import json, sys
with open(sys.argv[2], 'w') as f: json.dump({'project': '../..'}, f)
PY
codesign --force --sign - "$app"
printf 'Built %s\n' "$app"

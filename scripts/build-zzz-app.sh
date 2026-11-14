#!/bin/bash
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
app="$project_dir/dist/ZZZ Bridge.app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources" .build/steam-session
xcrun swiftc native/SteamBridge.swift -o "$app/Contents/MacOS/SteamBridge" -framework AppKit -module-cache-path .build/steam-session/module-cache
python3 - "$project_dir" "$app" <<'PY'
import json,plistlib,sys
from pathlib import Path
r=Path(sys.argv[2]);(r/'Contents/Resources/project.json').write_text(json.dumps({'project':'../..','game':'zzz'}))
p=dict(CFBundleExecutable='SteamBridge',CFBundleIdentifier='local.macwin.zzz',CFBundleName='ZZZ Bridge',CFBundleDisplayName='ZZZ Bridge',CFBundlePackageType='APPL',CFBundleShortVersionString='0.1.0',CFBundleVersion='1',LSMinimumSystemVersion='14.0',LSUIElement=True,NSHighResolutionCapable=True,CFBundleIconFile='ZZZBridge')
with (r/'Contents/Info.plist').open('wb') as f:plistlib.dump(p,f)
PY
xcrun swift -module-cache-path .build/steam-session/module-cache native/SteamIcon.swift "$app/Contents/Resources/ZZZBridge.iconset" ZZZ
iconutil -c icns "$app/Contents/Resources/ZZZBridge.iconset" -o "$app/Contents/Resources/ZZZBridge.icns"
codesign --force --sign - "$app"
codesign --verify --strict "$app"

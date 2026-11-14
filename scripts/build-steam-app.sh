#!/bin/bash
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
mkdir -p .build/steam-session
python3 - <<'PY'
from pathlib import Path
import subprocess, sys, fcntl, shutil
r=Path.cwd(); sys.path.insert(0,str(r/'scripts'))
from shared_storage import settings, environment
root,wine=settings(r);e=environment(r,root,wine)
out=r/'.build/steam-session/steam-window-watch.exe'
inputs=[r/'native/steam-window-watch.c',r/'native/steam_watch_state.h']
if not out.exists() or any(p.stat().st_mtime>out.stat().st_mtime for p in inputs):
    compiler=shutil.which('x86_64-w64-mingw32-gcc')
    if compiler:
        subprocess.run([compiler,'-O2','-Wall','-Wextra','-static',str(inputs[0]),'-luser32','-o',str(out)],check=True)
        sys.exit(0)
    if not (root/'prefixes/shared/system.reg').is_file():
        raise SystemExit('Install mingw-w64 with brew bundle to build without a Wine prefix.')
    maintenance=open(root/'steam-maintenance.lock','a')
    fcntl.flock(maintenance,fcntl.LOCK_EX|fcntl.LOCK_NB)
    subprocess.run([str(wine.parent/'wineserver'),'-w'],env=e,timeout=3,check=True)
    def wp(p): return 'Z:'+str(r/p).replace('/',chr(92))
    try:
        with open(r/'var/logs/build-steam-watch.log','w') as log:
            subprocess.run([str(wine),str(r/'.runtime/tinycc/tcc/tcc.exe'),'-o',wp('.build/steam-session/steam-window-watch.exe'),wp('native/steam-window-watch.c'),'-luser32'],env=e,stdout=log,stderr=log,check=True)
    finally:
        subprocess.run([str(wine.parent/'wineserver'),'-k'],env=e,check=True)
        subprocess.run([str(wine.parent/'wineserver'),'-w'],env=e,timeout=10,check=True)
PY

app="$project_dir/dist/Steam Bridge.app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
xcrun swiftc native/SteamBridge.swift -o "$app/Contents/MacOS/SteamBridge" -framework AppKit -module-cache-path .build/steam-session/module-cache
python3 - "$project_dir" "$app" <<'PY'
import json,plistlib,sys
from pathlib import Path
r=Path(sys.argv[2]); (r/'Contents/Resources/project.json').write_text(json.dumps({'project':'../..'}))
p=dict(CFBundleExecutable='SteamBridge',CFBundleIdentifier='local.macwin.steam',CFBundleName='Steam Bridge',CFBundleDisplayName='Steam Bridge',CFBundlePackageType='APPL',CFBundleShortVersionString='0.1.1',CFBundleVersion='2',LSMinimumSystemVersion='14.0',LSUIElement=True,NSHighResolutionCapable=True,CFBundleIconFile='SteamBridge')
with (r/'Contents/Info.plist').open('wb') as f:plistlib.dump(p,f)
PY
if [ ! -s "$app/Contents/Resources/SteamBridge.icns" ] || [ native/SteamIcon.swift -nt "$app/Contents/Resources/SteamBridge.icns" ]; then
xcrun swift -module-cache-path .build/steam-session/module-cache native/SteamIcon.swift "$app/Contents/Resources/SteamBridge.iconset"
iconutil -c icns "$app/Contents/Resources/SteamBridge.iconset" -o "$app/Contents/Resources/SteamBridge.icns"
fi
codesign --force --sign - "$app"
codesign --verify --strict "$app"

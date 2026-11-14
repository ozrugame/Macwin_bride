#!/bin/bash
# Diagnostic helper only; does not install over Steam or change launch defaults.
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
mkdir -p .build/webhelper
if command -v x86_64-w64-mingw32-gcc >/dev/null 2>&1; then
    x86_64-w64-mingw32-gcc -municode -O2 -Wall -Wextra -static -mwindows \
        third_party/steam-webhelper/steamwebhelper-wrapper.c \
        -o .build/webhelper/steamwebhelper.exe
else
    # TinyCC's normal CRT calls main; the upstream wrapper uses wmain but no argv.
    cat > .build/webhelper/entry.c <<'C'
int wmain(void);
int main(void) { return wmain(); }
C
    python3 - <<'PY'
from pathlib import Path
import os, subprocess, sys, fcntl
root = Path.cwd()
sys.path.insert(0,str(root/'scripts'))
from shared_storage import settings, environment
data_root,wine=settings(root)
tcc = root / '.runtime/tinycc/tcc/tcc.exe'
if not wine.is_file() or not tcc.is_file():
    raise SystemExit('Install mingw-w64, or provide the documented local Wine + TinyCC first.')
def windows_path(relative):
    return 'Z:' + str(root / relative).replace('/', '\\')
maintenance=open(data_root/'steam-maintenance.lock','a')
fcntl.flock(maintenance,fcntl.LOCK_EX|fcntl.LOCK_NB)
env = environment(root,data_root,wine)
subprocess.run([str(wine.parent/'wineserver'),'-w'],env=env,timeout=0.5,check=True)
try:
    subprocess.run([str(wine), str(tcc), '-Wl,-subsystem=gui', '-o',
                   windows_path('.build/webhelper/steamwebhelper.exe'),
                   windows_path('third_party/steam-webhelper/steamwebhelper-wrapper.c'),
                   windows_path('.build/webhelper/entry.c')], env=env, check=True)
finally:
    subprocess.run([str(wine.parent/'wineserver'),'-k'],env=env,check=True)
    subprocess.run([str(wine.parent/'wineserver'),'-w'],env=env,timeout=10,check=True)
PY
fi
file .build/webhelper/steamwebhelper.exe

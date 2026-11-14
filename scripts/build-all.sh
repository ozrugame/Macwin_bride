#!/bin/bash
# Used in a clean staging directory by make build/package.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v x86_64-w64-mingw32-gcc >/dev/null || { echo 'Run brew bundle first.' >&2; exit 1; }
bash scripts/build-webhelper.sh
bash scripts/build-app.sh
bash scripts/build-steam-app.sh
bash scripts/build-zzz-app.sh
bash scripts/swift.sh build -c release -debug-info-format none --product bridge
binary_dir="$(bash scripts/swift.sh build -c release --show-bin-path)"
mkdir -p bin
cp "$binary_dir/bridge" bin/bridge
for app in dist/*.app; do codesign --verify --strict "$app"; done

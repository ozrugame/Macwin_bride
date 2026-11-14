#!/bin/bash
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
export CLANG_MODULE_CACHE_PATH="$project_dir/.build/module-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="$project_dir/.build/module-cache"
subcommand="${1:-build}"
if [ "$#" -gt 0 ]; then shift; fi
developer_dir="$(xcode-select -p)"
exec swift "$subcommand" --disable-sandbox \
  --cache-path "$project_dir/.build/cache" \
  --config-path "$project_dir/.build/config" \
  --security-path "$project_dir/.build/security" \
  -Xswiftc -plugin-path -Xswiftc "$developer_dir/usr/lib/swift/host/plugins/testing" "$@"

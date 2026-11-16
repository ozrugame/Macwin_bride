# Building MacWin Bridge

## Requirements

- macOS 14+ for native app builds, Swift 6 toolchain / Xcode Command Line Tools.
- Python 3.9+ and the standard library; no pip dependencies.
- Homebrew `mingw-w64`: `brew bundle`.
- The build does not launch Wine, Steam, or games. macOS 14 is the launcher deployment target, not a guarantee that the selected graphics runtime works on macOS 14.

## Commands

```sh
make test
make privacy-check
make build
make package
```

`make build` exports only approved source files into a temporary staging directory and compiles there. Output: `.build/distribution/MacWinBridge`. `make package` repeats the clean build and produces `.artifacts/MacWinBridge-macos-<architecture>.tar.gz` and its SHA-256 file. Existing distributions containing `var/` or `.runtime/` are protected from overwrite; move that distribution before rebuilding.

The bundle contains:

- `dist/MacWin Bridge.app`, `dist/Steam Bridge.app`, `dist/ZZZ Bridge.app`
- `bin/bridge` CLI, `scripts/` and source/documentation
- `.build/webhelper/steamwebhelper.exe` and `.build/steam-session/steam-window-watch.exe`, compiled from included C source

No Wine engine, proprietary Steam/game binaries, GStreamer installation, ZZZ sidecar binaries, logs or account data are included. These must be provisioned separately; see [RUNTIME.md](RUNTIME.md).

The exporter checks source content for known credential patterns; the completed bundle is checked again for account files, private directories, symlinks and those patterns before it is published as build output. `make privacy-check` checks the Git index and all locally available Git history against the source allowlist and known credential patterns. CI fetches full history and runs this check before building. It does not log out or modify the developer's local accounts. These checks are guardrails, not a general-purpose secret detector.

Apps locate the project root relative to their containing bundle. Keep the extracted folder structure intact. Moving the whole unused bundle is supported; moving a configured Wine prefix or existing game library is a separate migration and is not implemented by the build scripts.

## GitHub Actions

Push to `main`, open a pull request, or use `workflow_dispatch` on **Build macOS launchers**. The workflow uses the Apple Silicon `macos-15` runner, installs `mingw-w64`, runs Swift/Python/C tests, builds the same package and uploads it as an artifact (30-day retention). The workflow has read-only repository permissions and does not publish a Release automatically.

Download the artifact from a successful run, extract the inner `.tar.gz`, and verify with:

```sh
shasum -a 256 -c MacWinBridge-macos-arm64.tar.gz.sha256
```

Apps are ad-hoc signed, not Developer ID signed or notarized. Distribution outside a development environment needs a separate signing/notarization setup.

## Existing personal installation

Use `make build/package` in the original checkout: they do not overwrite its running apps, helper hashes, Wine prefix or library. The lower-level `scripts/build-*.sh` write directly into their current checkout and are intended for clean staging/development. Do not replace a registered Steam wrapper with a differently compiled helper without updating its registration while Steam is stopped.

Tests cover source export exclusions, process ownership, Steam update repair, interrupted ZZZ recovery, shared library paths and window close behavior. Successful CI does not certify game performance, account authentication or compatibility after game updates.

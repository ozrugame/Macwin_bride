# Steam webhelper diagnostic wrapper

Source: https://github.com/notpop/steam-on-m1-wine
Commit: `540037ef96a3aa8f0bfee95d44e084d5402322a0`
Original path: `wrapper/src/steamwebhelper-wrapper.c`
License: MIT, copyright 2026 notpop (see LICENSE).

Source retained unmodified. From the project root:

```sh
bash scripts/build-webhelper.sh
```

Experimental only. Single-process mode changes Chromium process isolation. Do not deploy over the original Steam helper without a verified backup. Steam updates may restore or replace the helper. No game binaries or Valve binaries are distributed here.

The script uses mingw-w64 when available, otherwise project-local Wine + TinyCC. The tested compiler was downloaded from the [official TinyCC release directory](https://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip), extracted into `.runtime/tinycc`. Locally computed SHA256: `34a721949a2583fdff725312da092fa0f5f1f284b702e6f811c6954714faabb2` (record of downloaded bytes, not a publisher-provided digest). Compiler license remains inside the extracted package.

2026-10-11: compiled to an x86-64 Windows GUI executable. A real child-process fixture under Wine verified that both flags, an argument containing spaces, a literal shell expression and exit status 23 passed through correctly. This verifies the wrapper mechanics, not Steam rendering.

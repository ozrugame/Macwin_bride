# Runtime requirements

The repository builds launchers. It does **not** yet bootstrap a playable Wine environment on a fresh Mac. The existing installation was configured and qualified separately. Downloading a successful CI artifact alone is not enough to play a game.

## Expected layout

Relative to the extracted project/package root:

```text
.runtime/sikarugir/wswine.bundle/bin/wine
.runtime/sikarugir/wswine.bundle/bin/wineserver
.runtime/gstreamer-video-plugins/libgstlibav.dylib
.runtime/zzz-support/steam.exe             # optional: ZZZ
.runtime/zzz-support/lsteamclient.dll      # optional: ZZZ
var/prefixes/shared/system.reg
var/prefixes/shared/drive_c/Program Files (x86)/Steam -> var/Steam
var/Steam/Steam.exe
var/Steam/.macwin-webhelper.json
```

The Steam link must resolve to the central `var/Steam` directory (use an absolute target or a correct relative symlink, not the illustrative text above). Wine and Steam must be installed by their own supported procedures before these launchers are used. `bridge init`/`install-steam` currently open an existing installation; they do not provision a new one.

The qualified local combination uses Sikarugir Wine 11.0 with DXMT v0.80 and GStreamer 1.28.7 x86_64 libraries/plugins. Apple Silicon also needs Rosetta for the x86_64 runtime. `shared_storage.environment` configures the required paths and `SikarugirAppWine11=1`. The GStreamer framework is expected under `/Library/Frameworks/GStreamer.framework` and plugins under the project directory. Runtime installation, graphics DLL configuration, licensing and dependency setup are separate from building source.

A prepared environment also needs the Steam UI wrapper registered with both SHA-256 values in `.macwin-webhelper.json`: the compiled wrapper at `bin/cef/cef.win64/steamwebhelper.exe` and the original Valve helper at `steamwebhelper_real.exe`. The repair code checks these and Steam's installed package manifest. Do not copy another person's prefix or marker: it can contain accounts/saves and refer to a different helper build.

## ZZZ sidecars

The tested sidecars originate from [YAAGL](https://github.com/yaagl/yet-another-anime-game-launcher/tree/main/sidecar/protonextras). They are not bundled or downloaded automatically. The launcher requires these exact SHA-256 values and refuses other binaries:

| Destination | Upstream filename | SHA-256 |
| --- | --- | --- |
| `.runtime/zzz-support/steam.exe` | `steam64.exe` | `0424339444c54bf1f9fdbadf12e4e2c90ceef41d987fe573b93f5f2ebfd8a657` |
| `.runtime/zzz-support/lsteamclient.dll` | `lsteamclient64.dll` | `af50ed0d952ef98d99d4d3ff67b4836b545c9403894430fca31969f9f630637b` |

Use the same single shared Wine runtime; the experimental second runtime was not required. The installed ZZZ game path is `var/Steam/steamapps/common/Zenless Zone Zero/games/ZenlessZoneZero Game`. ZZZ Bridge selects HoYoverse login temporarily and restores Steam settings after exit. Steam must be closed while ZZZ Bridge runs. Use Steam normally to install/update the game after ZZZ exits.

## Read-only checks

```sh
bin/bridge doctor --profile world
python3 scripts/launch-limbus.py --check
python3 scripts/zzz_session.py --check
```

Missing dependencies are reported; these commands do not download games or initialize another prefix. Keep all account data, saves and diagnostic logs local.

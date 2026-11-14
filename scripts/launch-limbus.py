#!/usr/bin/env python3
"""Open Limbus through the shared Steam environment."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime


def prepare(project, root=None, wine=None, verify_helper=True):
    from shared_storage import settings, environment
    root, wine = settings(project, root, wine)
    prefix = root / "prefixes/shared"
    steam = prefix / "drive_c/Program Files (x86)/Steam"
    plugins = project / ".runtime/gstreamer-video-plugins"
    required = [wine, wine.parent / "wineserver", prefix / "system.reg",
                steam / "Steam.exe", plugins / "libgstlibav.dylib"]
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"ไม่พบไฟล์ที่จำเป็นในชุดกลาง: {path}")
    if steam.resolve() != (root / "Steam").resolve():
        raise RuntimeError("Steam ยังไม่ได้ใช้คลังกลาง กรุณาย้ายข้อมูลก่อนเปิด")
    if verify_helper:
        from steam_update import validate
        validate(steam)
    env = environment(project, root, wine)
    args = [str(wine), str(steam / "Steam.exe"), "-noverifyfiles"]
    return args, env, steam


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate without launching")
    options = parser.parse_args()
    project = Path(__file__).resolve().parent.parent
    try:
        args, env, steam = prepare(project, verify_helper=options.check)
        if options.check:
            print("ตรวจชุดกลางและตัวช่วย Steam ผ่านแล้ว")
            return 0
        logs = project / "var/logs"
        logs.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        log = logs / f"limbus-shared-{stamp}.log"
        with log.open("xb") as output:
            subprocess.Popen([sys.executable, str(project / "scripts/steam_session.py"), "--limbus"],
                             cwd=project, env=env, stdout=output,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             start_new_session=True)
        print("กำลังเปิด Limbus Company ผ่าน Steam")
        print(f"บันทึกการเปิดเกม: {log}")
        return 0
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(f"เปิดเกมไม่ได้: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

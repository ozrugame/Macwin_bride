"""Own one Wine session until Steam's main window closes or the launcher quits."""
import argparse
import fcntl
import importlib.util
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import threading
from datetime import datetime


def limbus_launch_options(text):
    """Patch just Limbus' direct LaunchOptions value, preserving other VDF bytes."""
    tokens = list(re.finditer(r'"(?:\\.|[^"\\])*"|[{}]|//[^\n]*', text))
    tokens = [t for t in tokens if not t.group().startswith('//')]
    stack = []
    for i, token in enumerate(tokens):
        value = token.group()
        if value == '{': stack.append(tokens[i-1].group().strip('"').lower())
        elif value == '}':
            if stack: stack.pop()
        elif value == '"1973530"' and stack and stack[-1] == 'apps' and tokens[i+1].group() == '{':
            depth = 1; j = i + 2
            while j < len(tokens) and depth:
                t = tokens[j]
                if t.group() == '{': depth += 1
                elif t.group() == '}': depth -= 1
                elif depth == 1 and t.group().lower() == '"launchoptions"':
                    current = tokens[j+1]
                    if not current.group().startswith('"'): raise RuntimeError('Steam launch options ไม่ถูกต้อง')
                    raw = current.group()[1:-1]
                    flag = '-video-allow-hw-acceleration'
                    if flag in raw:
                        updated = re.sub(r'-video-allow-hw-acceleration(?:\s+\S+)?', flag+' 0', raw)
                    else: updated = (raw+' '+flag+' 0').strip()
                    return text[:current.start()]+'"'+updated+'"'+text[current.end():]
                if depth == 0:
                    return text[:t.start()]+'\n\t\t\t\t"LaunchOptions"\t\t"-video-allow-hw-acceleration 0"\n'+text[t.start():]
                j += 1
    raise RuntimeError('ไม่พบการตั้งค่า Limbus ใน Steam จึงยังไม่แก้ไฟล์')


def persist_game_options(project, steam, wine, env):
    try:
        state = subprocess.run([str(wine.parent/'wineserver'), '-w'], env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5)
    except subprocess.TimeoutExpired:
        return  # Never edit Steam-owned configuration while it is running.
    if state.returncode: raise RuntimeError('ตรวจสถานะ Steam ก่อนบันทึกค่าล้มเหลว')
    files = list((steam/'userdata').glob('*/config/localconfig.vdf'))
    if len(files) != 1: return  # Generic Steam startup must not depend on one account.
    path = files[0]; original = path.read_text()
    try: updated = limbus_launch_options(original)
    except RuntimeError: return  # Limbus may not be installed for this account.
    if updated == original: return
    backup = project/'var/backups/limbus-steam-launch-options'
    backup.mkdir(parents=True, exist_ok=True)
    saved = backup/'localconfig.vdf'
    if not saved.exists(): saved.write_bytes(path.read_bytes()); saved.chmod(0o600)
    temporary = path.with_suffix('.vdf.macwin-tmp')
    temporary.write_text(updated); temporary.chmod(path.stat().st_mode & 0o777)
    os.replace(temporary, path)


def shutdown(wine, steam, env, grace=20):
    server = wine.parent / "wineserver"
    common = dict(env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Normal close first, including games; then clean up this prefix only.
    for args in ([str(wine), str(steam), "-noverifyfiles", "-shutdown"],
                 [str(wine), "wineboot", "-e", "-s"]):
        try:
            subprocess.run(args, timeout=5, **common)
        except subprocess.TimeoutExpired:
            pass
    try:
        result = subprocess.run([str(server), "-w"], timeout=grace, **common)
        if result.returncode == 0:
            return
    except subprocess.TimeoutExpired:
        pass
    subprocess.run([str(server), "-k"], timeout=5, **common)
    result = subprocess.run([str(server), "-w"], timeout=10, **common)
    if result.returncode:
        raise RuntimeError("ยังยืนยันไม่ได้ว่าปิด Wine ครบ กรุณาตรวจ log")


def session_options(argv):
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--limbus', action='store_true')
    group.add_argument('--app-id', choices=['1973530','582010','1446780'])
    group.add_argument('--install-app', choices=['1973530','582010','1446780'])
    parser.add_argument('--root')
    parser.add_argument('--wine')
    return parser.parse_args(argv)


def steam_arguments(base, argv):
    opts=session_options(argv)
    if opts.install_app: return base+['steam://install/'+opts.install_app]
    app='1973530' if opts.limbus else opts.app_id
    if not app: return base
    args=base+['-applaunch',app]
    if app=='1973530': args+=['-video-allow-hw-acceleration','0']
    return args


def run_session():
    project = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("limbus_launch", project / "scripts/launch-limbus.py")
    launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    options = session_options(sys.argv[1:])
    args, env, steam_dir = launcher.prepare(project, options.root, options.wine, verify_helper=False)
    args = steam_arguments(args, sys.argv[1:])
    data_root = Path(env["WINEPREFIX"]).parent.parent
    watcher = project / ".build/steam-session/steam-window-watch.exe"
    if not watcher.is_file():
        raise RuntimeError("ไม่พบตัวช่วยปิด Steam กรุณาสร้างแอปใหม่")
    ready = data_root / "steam-session.ready"
    lock = open(data_root / "steam-session.lock", "a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        # Do not start a second Steam while the owner is updating it.
        if ready.is_file():
            subprocess.Popen(args, env=env, cwd=steam_dir, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        lock.close()
        print("already-managed", flush=True)
        return 0
    ready.unlink(missing_ok=True)
    log_path = data_root / "logs" / ("managed-steam-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    watch = None
    reader = None
    started = False
    try:
        with log_path.open("xb") as log:
            from steam_update import initialize_client, prefix_idle
            idle = prefix_idle(Path(args[0]), env)
            started = idle  # Own updater cleanup, but don't close an unrelated active game on preflight failure.
            initialize_client(project, steam_dir, Path(args[0]), env, log, stop, idle=idle)
            persist_game_options(project, steam_dir, Path(args[0]), env)
            subprocess.Popen(args, cwd=steam_dir, env=env, stdout=log, stderr=log,
                             stdin=subprocess.DEVNULL)
            started = True
            watch = subprocess.Popen([args[0], str(watcher)], cwd=steam_dir, env=env,
                                     stdout=subprocess.PIPE, stderr=log, text=True)
            # Relay readiness; keep the session supervisor running without a control window.
            def relay():
                for line in watch.stdout:
                    if line.strip() == "watching":
                        log.write(b"\nbridge:watching\n"); log.flush()
                        ready.write_text(str(os.getpid()))
                        print("watching", flush=True)
            reader = threading.Thread(target=relay, daemon=True); reader.start()
            while watch.poll() is None and not stop.wait(0.25):
                pass
            status = watch.poll()
            if status not in (None, 0):
                print("watch-error", flush=True)
            print("stopping", flush=True)
            if watch.poll() is None:
                watch.terminate()
                try: watch.wait(timeout=3)
                except subprocess.TimeoutExpired: watch.kill(); watch.wait()
            shutdown(Path(args[0]), Path(args[1]), env)
            started = False
            print("stopped", flush=True)
            return 0 if status in (None, 0) else 2
    finally:
        try:
            if watch and watch.poll() is None:
                watch.kill(); watch.wait()
            if reader: reader.join(timeout=3)
            ready.unlink(missing_ok=True)
            if started and not prefix_idle(Path(args[0]), env):
                shutdown(Path(args[0]), Path(args[1]), env)
        finally:
            lock.close()


def main():
    from shared_storage import settings
    project = Path(__file__).resolve().parents[1]
    options = session_options(sys.argv[1:])
    root, _ = settings(project, options.root, options.wine)
    with open(root / 'steam-maintenance.lock', 'a') as maintenance:
        try: fcntl.flock(maintenance, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            if (root / 'zzz-session.json').exists():
                raise RuntimeError('ZZZ กำลังใช้ Bridge อยู่ กรุณาออกจาก ZZZ ก่อนเปิด Steam')
            raise RuntimeError('กำลังปรับปรุงตัวเปิด Steam กรุณารอให้เสร็จก่อนเปิดอีกครั้ง')
        return run_session()


if __name__ == "__main__":
    try: sys.exit(main())
    except Exception as error:
        print(str(error), file=sys.stderr, flush=True)
        sys.exit(1)

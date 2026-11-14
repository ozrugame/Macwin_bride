"""Launch the shared ZZZ installation with HoYoverse login, then restore Steam settings."""
import argparse
import base64
from datetime import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading

from shared_storage import settings, environment
from steam_update import atomic_write, prefix_idle

HELPERS = {
    'steam.exe': '0424339444c54bf1f9fdbadf12e4e2c90ceef41d987fe573b93f5f2ebfd8a657',
    'lsteamclient.dll': 'af50ed0d952ef98d99d4d3ff67b4836b545c9403894430fca31969f9f630637b',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def paths(root):
    return (root/'Steam/steamapps/common/Zenless Zone Zero/games/ZenlessZoneZero Game',
            root/'prefixes/shared/drive_c/windows/system32', root/'zzz-session.json')


def login_config(original):
    section = re.search(rb'(?ims)^\[General\][^\r\n]*\r?\n(.*?)(?=^\[|\Z)', original)
    if not section: raise RuntimeError('ไม่พบการตั้งค่า General ของ ZZZ')
    content = section.group(1)
    def value(key):
        matches = re.findall(rb'(?m)^'+key+rb'=([^\r\n]*)', content)
        if len(matches) != 1: raise RuntimeError('การตั้งค่าช่องทาง ZZZ ไม่สมบูรณ์')
        return matches[0]
    if value(b'channel') != b'1' or (value(b'sub_channel'),value(b'cps')) not in ((b'5',b'Steam'),(b'0',b'mihoyo')):
        raise RuntimeError('ช่องทาง ZZZ ไม่ตรงกับรุ่นที่ทดสอบไว้ จึงยังไม่เปลี่ยนค่า')
    content = re.sub(rb'(?m)^sub_channel=[^\r\n]*', b'sub_channel=0', content)
    content = re.sub(rb'(?m)^cps=[^\r\n]*', b'cps=mihoyo', content)
    return original[:section.start(1)] + content + original[section.end(1):]


def begin(project, root):
    """Caller holds both locks and has verified Wine is stopped. Journal first."""
    game, system, journal = paths(root)
    if journal.exists(): raise RuntimeError('ยังมีค่าจากรอบก่อน ต้องคืนค่าก่อนเปิด ZZZ')
    original = (game/'config.ini').read_bytes()
    configured = login_config(original)
    data = {}
    for name, expected in HELPERS.items():
        if (system/name).exists(): raise RuntimeError('พบตัวช่วย Wine เดิม จึงไม่เขียนทับ: '+name)
        data[name] = (project/'.runtime/zzz-support'/name).read_bytes()
        if digest(data[name]) != expected: raise RuntimeError('ไฟล์ตัวช่วย ZZZ ไม่ตรงกับรุ่นที่ตรวจไว้: '+name)
    state = dict(version=1, original=base64.b64encode(original).decode(), configured=digest(configured), helpers=HELPERS)
    atomic_write(journal, json.dumps(state,indent=2).encode())
    for name, content in data.items(): atomic_write(system/name,content)
    atomic_write(game/'config.ini',configured)


def recover(root):
    """Idempotent recovery after normal exit or interruption, only while Wine is idle."""
    game, system, journal = paths(root)
    if not journal.exists(): return
    state = json.loads(journal.read_text())
    if state.get('version') != 1 or state.get('helpers') != HELPERS:
        raise RuntimeError('บันทึกคืนค่า ZZZ ไม่ตรงกับรุ่นที่ตรวจไว้')
    original = base64.b64decode(state['original'],validate=True)
    current = (game/'config.ini').read_bytes()
    if current != original and digest(current) != state['configured']:
        raise RuntimeError('ไฟล์ตั้งค่า ZZZ เปลี่ยนระหว่างเล่น จึงเก็บสำรองไว้ที่ '+str(journal))
    for name, expected in HELPERS.items():
        target=system/name
        if target.exists() and digest(target.read_bytes()) != expected:
            raise RuntimeError('ตัวช่วย ZZZ ถูกเปลี่ยน จึงไม่ลบไฟล์: '+name)
    atomic_write(game/'config.ini',original)
    for name in HELPERS: (system/name).unlink(missing_ok=True)
    journal.unlink()


def stop_wine(wine, env):
    common=dict(env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if prefix_idle(wine,env): return
    try: subprocess.run([str(wine),'wineboot','-e','-s'],timeout=8,**common)
    except subprocess.TimeoutExpired: pass
    try: subprocess.run([str(wine.parent/'wineserver'),'-w'],timeout=15,check=True,**common)
    except (subprocess.TimeoutExpired,subprocess.CalledProcessError):
        subprocess.run([str(wine.parent/'wineserver'),'-k'],timeout=5,check=True,**common)
        subprocess.run([str(wine.parent/'wineserver'),'-w'],timeout=10,check=True,**common)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    options=parser.parse_args(argv)
    project=Path(__file__).resolve().parents[1]
    root,wine=settings(project)
    game,system,journal=paths(root)
    env=environment(project,root,wine)
    # Keep the tested original-runtime environment. The timeout flag is harmless
    # on this build and retained from the controlled, user-verified trial.
    env['WINE_ENABLE_TIMEOUT_FIX']='1'
    for key in ('SteamGameId','SteamAppId','STEAM_COMPAT_CLIENT_INSTALL_PATH'):env.pop(key,None)
    for path in (wine,wine.parent/'wineserver',game/'ZenlessZoneZero.exe',game/'config.ini'):
        if not path.is_file():raise RuntimeError('ไม่พบไฟล์สำหรับเปิด ZZZ: '+str(path))
    for name,expected in HELPERS.items():
        if digest((project/'.runtime/zzz-support'/name).read_bytes()) != expected:
            raise RuntimeError('ตัวช่วย ZZZ ไม่ผ่านการตรวจ: '+name)
    if options.check:
        login_config((game/'config.ini').read_bytes())
        print('ตรวจตัวเปิด ZZZ ผ่าน ใช้ Wine และคลังเกมชุดกลาง');return 0
    stop=threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:stop.set())
    with (root/'steam-maintenance.lock').open('a') as maintenance, (root/'steam-session.lock').open('a') as session:
        try:
            fcntl.flock(maintenance,fcntl.LOCK_EX|fcntl.LOCK_NB)
            fcntl.flock(session,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('กรุณาปิด Steam หรือ ZZZ ที่เปิดอยู่ก่อน แล้วเปิด ZZZ Bridge อีกครั้ง')
        if not prefix_idle(wine,env):raise RuntimeError('กรุณาปิด Steam และเกมอื่นใน Bridge ก่อนเปิด ZZZ')
        recover(root)
        log=root/'logs'/('zzz-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.log')
        log.parent.mkdir(exist_ok=True)
        started=False
        try:
            begin(project,root)
            if stop.is_set():return 0
            winexe=r'C:\Program Files (x86)\Steam\steamapps\common\Zenless Zone Zero\games\ZenlessZoneZero Game\ZenlessZoneZero.exe'
            with log.open('xb') as output:
                started=True
                child=subprocess.Popen([str(wine),r'C:\windows\system32\steam.exe',winexe],cwd=game,env=env,
                                       stdout=output,stderr=output,stdin=subprocess.DEVNULL)
                print('กำลังเปิด ZZZ — เข้าด้วยบัญชี HoYoverse',flush=True)
                while child.poll() is None and not stop.wait(0.25):pass
                code=child.poll()
                if code not in (None,0):raise RuntimeError('ZZZ ปิดด้วยข้อผิดพลาด ดู log ที่ '+str(log))
        finally:
            # Keep recovery pending if shutdown fails; never change files in use.
            if started:stop_wine(wine,env)
            recover(root)
        print('ปิด ZZZ และ Wine แล้ว คืนค่าช่องทาง Steam เรียบร้อย',flush=True)
        return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as error:
        print(str(error),file=sys.stderr,flush=True);sys.exit(1)

"""Repair the registered UI wrapper after Valve's updater finishes.

Caller must own the session lock and confirm this prefix's Wine server is idle.
Only the two UI helper files and their marker are written; no game library copies.
"""
import hashlib
import json
import os
import re
import struct
import subprocess
import tempfile
import time
import zlib


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record_for(steam):
    try:
        record = json.loads((steam / '.macwin-webhelper.json').read_text())
        for key in ('wrapperSHA256', 'originalSHA256'):
            if not re.fullmatch(r'[0-9a-f]{64}', record[key]): raise ValueError(key)
        return record
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RuntimeError('ข้อมูลตัวช่วย Steam ไม่สมบูรณ์ กรุณาตรวจ log') from error


def validate(steam):
    record = record_for(steam)
    folder = steam / 'bin/cef/cef.win64'
    try:
        for name, key in [('steamwebhelper.exe', 'wrapperSHA256'),
                          ('steamwebhelper_real.exe', 'originalSHA256')]:
            if digest((folder / name).read_bytes()) != record[key]:
                raise ValueError(name)
    except (OSError, ValueError) as error:
        raise RuntimeError('ตัวช่วย Steam ต้องซ่อมหลังอัปเดต กรุณาปิด Steam แล้วเปิดผ่านไอคอนอีกครั้ง') from error


def atomic_write(path, data):
    fd, temporary = tempfile.mkstemp(prefix='.macwin-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data); output.flush(); os.fsync(output.fileno())
        os.chmod(temporary, (path.stat().st_mode & 0o777) if path.exists() else 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def official_helper(steam, data):
    """Check x64 PE, size and CRC against Steam's installed-file manifest."""
    try:
        table = (steam / 'package/steam_client_win64.installed').read_text()
        row = next(line.split(',', 1)[1] for line in table.splitlines()
                   if line.split(',', 1)[0].lower() == r'bin\cef\cef.win64\steamwebhelper.exe')
        size, _, crc = row.split(';')
        offset = struct.unpack_from('<I', data, 60)[0]
        if (len(data) != int(size) or zlib.crc32(data) != int(crc)
                or data[:2] != b'MZ' or data[offset:offset+6] != b'PE\0\0\x64\x86'):
            raise ValueError('helper does not match installed manifest')
        manifest = (steam / 'package/steam_client_win64.manifest').read_text()
        return re.search(r'"version"\s*"(\d+)"', manifest).group(1)
    except (OSError, ValueError, StopIteration, struct.error, AttributeError) as error:
        raise RuntimeError('ไฟล์ตัวช่วยจาก Steam ไม่ตรงกับข้อมูลติดตั้ง จึงยังไม่แทนที่ไฟล์ กรุณาลองเปิดอีกครั้ง') from error


def repair(project, steam):
    record = record_for(steam)
    folder = steam / 'bin/cef/cef.win64'
    helper = folder / 'steamwebhelper.exe'; real = folder / 'steamwebhelper_real.exe'
    try:
        validate(steam)
        return False
    except RuntimeError:
        pass
    built = project / '.build/webhelper/steamwebhelper.exe'
    wrapper = built.read_bytes()
    if digest(wrapper) != record['wrapperSHA256']:
        raise RuntimeError('ตัวช่วยที่สร้างไว้ไม่ตรงกับรุ่นที่ลงทะเบียน จึงยังไม่แก้ไฟล์ Steam')
    # If interrupted after restoring the wrapper, recover from the new real helper.
    current = helper.read_bytes() if helper.exists() else b''
    candidate = real.read_bytes() if digest(current) == record['wrapperSHA256'] or not current else current
    version = official_helper(steam, candidate)
    atomic_write(real, candidate)
    atomic_write(helper, wrapper)
    updated = dict(record, originalSHA256=digest(candidate), clientBuild=version)
    atomic_write(steam / '.macwin-webhelper.json', (json.dumps(updated, indent=2)+'\n').encode())
    validate(steam)
    return True


def prefix_idle(wine, env):
    try:
        result = subprocess.run([str(wine.parent / 'wineserver'), '-w'], env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
    except subprocess.TimeoutExpired:
        return False
    if result.returncode: raise RuntimeError('ตรวจสถานะ Wine ไม่สำเร็จ')
    return True


def update_client(wine, steam, env, log, stop, timeout=1800):
    """Valve checks versions/downloads only needed packages, then exits before UI."""
    print('updating-steam', flush=True)
    bootstrap = steam / 'logs/bootstrap_log.txt'
    offset = bootstrap.stat().st_size if bootstrap.exists() else 0
    args = [str(wine), str(steam / 'Steam.exe'), '-noverifyfiles', '-forcesteamupdate', '-exitsteam']
    child = subprocess.Popen(args, cwd=steam, env=env, stdout=log, stderr=log,
                             stdin=subprocess.DEVNULL)
    deadline = time.monotonic() + timeout
    while child.poll() is None:
        if stop.wait(0.25):
            raise RuntimeError('ยกเลิกการเปิด Steam')
        if time.monotonic() >= deadline:
            raise RuntimeError('Steam อัปเดตนานเกินกำหนด กรุณาตรวจเครือข่ายแล้วเปิดอีกครั้ง')
    try:
        with bootstrap.open('rb') as source:
            source.seek(offset)
            fresh = source.read().decode('utf-8', errors='replace')
    except OSError:
        fresh = ''
    # -exitsteam returns -2 (254 on Unix) even after a successful update check.
    # Never accept that code based on stale log entries from a previous run.
    complete = ('Nothing to do' in fresh or 'Update complete' in fresh) and 'Shutdown' in fresh
    if child.returncode not in (0, 254) or not complete:
        raise RuntimeError(f'Steam updater ยังยืนยันว่าเสร็จไม่ได้ (รหัส {child.returncode}) กรุณาตรวจ log')
    # Steam may have relaunched its bootstrapper; never repair files still in use.
    subprocess.run([str(wine.parent / 'wineserver'), '-w'], env=env,
                   stdout=log, stderr=log, timeout=30, check=True)


def initialize_client(project, steam, wine, env, log, stop, idle=None):
    if idle is None: idle = prefix_idle(wine, env)
    if idle:
        from zzz_session import recover
        recover(steam.resolve().parent)
        update_client(wine, steam, env, log, stop)
        if stop.is_set(): raise RuntimeError('ยกเลิกการเปิด Steam')
        if repair(project, steam): print('repaired-steam-helper', flush=True)
    validate(steam)

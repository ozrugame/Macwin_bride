"""One shared Wine environment and Steam library; offline rename-only migration."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse, unquote


def settings(project, root=None, wine=None):
    config = project/'var/config.json'
    saved = json.loads(config.read_text()) if config.exists() else {}
    def path(value):
        return Path(unquote(urlparse(value).path)) if value.startswith('file:') else Path(value)
    root = Path(root) if root else path(saved['root']) if 'root' in saved else project/'var'
    wine = Path(wine) if wine else path(saved['wine']) if 'wine' in saved else project/'.runtime/sikarugir/wswine.bundle/bin/wine'
    if root.resolve() != (project/'var').resolve():
        raise RuntimeError('ใช้คลังกลาง var ของโปรเจกต์นี้เท่านั้น กรุณาย้ายข้อมูลก่อนเปลี่ยน root')
    return root, wine


def environment(project, root, wine):
    env = os.environ.copy()
    env.update(SikarugirAppWine11='1', WINEPREFIX=str(root/'prefixes/shared'),
        DYLD_FALLBACK_LIBRARY_PATH=str(wine.parent.parent/'lib')+':/Library/Frameworks/GStreamer.framework/Libraries:/usr/lib',
        WINEDEBUG='fixme-all', WINEDLLOVERRIDES='winemenubuilder.exe=d',
        GST_PLUGIN_SYSTEM_PATH_1_0=str(project/'.runtime/gstreamer-video-plugins'),
        GST_PLUGIN_PATH_1_0='', GST_REGISTRY=str(root/'probes/gst-video-registry.bin'),GST_REGISTRY_FORK='no')
    return env


def migrate(project):
    """Caller must stop both Wine servers. Never copies game data or overwrites a destination."""
    root=project/'var'; old=root/'prefixes/world'; source=root/'prefixes/limbus-dxmt'
    shared=root/'prefixes/shared'; central=root/'Steam'; journal=root/'shared-storage-migration.json'
    sub=Path('drive_c/Program Files (x86)/Steam')
    link=shared/sub
    if journal.exists():
        state=json.loads(journal.read_text())
        if state['status']=='complete' and link.is_symlink() and link.resolve()==central.resolve() and (central/'Steam.exe').is_file():
            return
        if state['status']!='rolled-back':
            raise RuntimeError('Migration journal requires inspection before retrying')
    if shared.exists() or central.exists() or source.is_symlink() or old.is_symlink():
        raise RuntimeError('Shared storage destination already exists or legacy source is an alias')
    if not (source/sub/'Steam.exe').is_file() or not (source/'system.reg').is_file():
        raise RuntimeError('Working Steam environment is missing')
    oldapps=old/sub/'steamapps'; apps=central/'steamapps'
    plans=[(source,shared),(shared/sub,central)]
    for relative in ['downloading/582010','appmanifest_582010.acf','temp/582010','common/Monster Hunter World']:
        src=oldapps/relative
        if src.exists():
            # Existing empty clone temp/common folders can be retained; never overwrite nonempty data.
            existing=source/sub/'steamapps'/relative
            if existing.exists():
                if src.is_dir() and not any(src.iterdir()): continue
                raise RuntimeError('Conflicting game destination: '+relative)
            plans.append((src,apps/relative))
    # Steam depot download checkpoint manifests are outside steamapps.
    depot=old/sub/'depotcache'
    if depot.exists():
        for src in depot.iterdir():
            if src.name.startswith(('582011_','582010_','960781_')) and not (source/sub/'depotcache'/src.name).exists():
                plans.append((src,central/'depotcache'/src.name))
    state={'status':'moving','moves':[]}
    def save():
        tmp=journal.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2));os.replace(tmp,journal)
    save(); done=[]; linked=False
    try:
        for src,dst in plans:
            if dst.exists(): raise RuntimeError('Destination exists: '+str(dst))
            dst.parent.mkdir(parents=True,exist_ok=True)
            os.rename(src,dst);done.append((src,dst))
            state['moves'].append([str(src.relative_to(project)),str(dst.relative_to(project))]);save()
        link.symlink_to(os.path.relpath(central,link.parent),target_is_directory=True);linked=True
        state['status']='complete';save()
    except Exception:
        if linked:link.unlink()
        for src,dst in reversed(done):
            src.parent.mkdir(parents=True,exist_ok=True);os.rename(dst,src)
        state['status']='rolled-back';save()
        raise


if __name__=='__main__':
    import subprocess, fcntl
    project=Path(__file__).resolve().parents[1]
    with open(project/'var/steam-session.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for name, wine in [('limbus-dxmt',project/'.runtime/sikarugir/wswine.bundle/bin/wine'),('world',project/'.runtime/Wine Devel.app/Contents/Resources/wine/bin/wine')]:
            if not (project/'var/prefixes'/name).exists(): continue
            env=environment(project,project/'var',wine)
            env['WINEPREFIX']=str(project/'var/prefixes'/name)
            # Migration runs before the original dependency directory is retired.
            env['DYLD_FALLBACK_LIBRARY_PATH']=str(project/'.runtime/Wine Devel.app/Contents/Resources/wine/lib')+':'+env['DYLD_FALLBACK_LIBRARY_PATH']
            subprocess.run([str(wine.parent/'wineserver'),'-w'],env=env,timeout=1,check=True)
        migrate(project)
    print('Shared Steam migration complete; existing game files moved without copying.')

"""Build an isolated, relocatable source + launcher bundle; never copy user data."""
import argparse
import hashlib
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
from privacy_check import check_bundle, check_content, check_path

ROOT_FILES={'.gitignore','Package.swift','README.md','Brewfile','Makefile','NOTICE.md'}
TREES={'Sources':{'.swift'},'native':{'.swift','.c','.h'},'Tests':{'.swift','.py','.c'},
       'scripts':{'.py','.sh'},'.github':{'.yml','.yaml'},'diagnostics':{'.c'}}
EXTRA={'docs/BUILD.md','docs/RUNTIME.md','third_party/steam-webhelper/README.md',
       'third_party/steam-webhelper/LICENSE','third_party/steam-webhelper/steamwebhelper-wrapper.c'}


def source_files(root):
    for name in sorted(ROOT_FILES|EXTRA):
        p=root/name
        if p.is_symlink():raise RuntimeError('Refusing source symlink: '+name)
        if p.is_file():yield p
    for name,suffixes in TREES.items():
        tree=root/name
        if tree.is_symlink():raise RuntimeError('Refusing source symlink: '+name)
        for p in sorted(tree.rglob('*')):
            if p.is_symlink():raise RuntimeError('Refusing source symlink: '+str(p.relative_to(root)))
            if p.is_file() and p.suffix in suffixes and '__pycache__' not in p.parts:yield p


def export_source(root,out):
    for src in source_files(root):
        check_path(src.relative_to(root).as_posix())
        check_content(src.relative_to(root).as_posix(), src.read_bytes())
        dest=out/src.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dest)


def prune_build(stage):
    def remove(item):
        # SwiftPM's release/debug entries are symlinks, not owned directory trees.
        if item.is_symlink() or not item.is_dir(): item.unlink()
        else: shutil.rmtree(item)
    for item in (stage/'.build').iterdir():
        if item.name not in ('webhelper','steam-session'): remove(item)
    for folder,keep in [('webhelper','steamwebhelper.exe'),('steam-session','steam-window-watch.exe')]:
        for item in (stage/'.build'/folder).iterdir():
            if item.name!=keep: remove(item)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['build','package']);args=parser.parse_args()
    if platform.system()!='Darwin':raise SystemExit('Build requires macOS with Swift 6 and Xcode Command Line Tools.')
    if not shutil.which('x86_64-w64-mingw32-gcc'):raise SystemExit('Missing mingw-w64. Install with: brew bundle')
    root=Path(__file__).resolve().parents[1]
    target=root/'.build/distribution/MacWinBridge'
    if (target/'var').exists() or (target/'.runtime').exists():
        raise SystemExit('Existing distribution contains user data. Move it before rebuilding.')
    (root/'.build').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='distribution-',dir=root/'.build') as tmp:
        stage=Path(tmp)/'MacWinBridge';export_source(root,stage)
        subprocess.run(['bash','scripts/build-all.sh'],cwd=stage,check=True)
        # Ship exactly the two Windows helpers, not compiler caches or Swift build state.
        prune_build(stage)
        for cache in stage.rglob('__pycache__'):shutil.rmtree(cache)
        check_bundle(stage)
        if target.exists():shutil.rmtree(target)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(stage),target)
    print('Build ready:',target)
    if args.action=='package':
        output=root/'.artifacts';output.mkdir(exist_ok=True)
        archive=output/('MacWinBridge-macos-'+platform.machine()+'.tar.gz')
        with tarfile.open(archive,'w:gz') as bundle:bundle.add(target,arcname='MacWinBridge')
        checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_suffix(archive.suffix+'.sha256').write_text(checksum+'  '+archive.name+'\n')
        print('Package:',archive)

if __name__=='__main__':main()

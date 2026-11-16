"""Reject known account files and credentials without printing their contents."""
import argparse
from pathlib import Path, PurePosixPath
import re
import subprocess


PRIVATE_DIRS = {'.git', '.runtime', '.downloads', '.remember', '.aws',
                'var', 'userdata', 'htmlcache', 'webcache', 'configstore'}
PRIVATE_FILES = {'loginusers.vdf', 'localconfig.vdf', 'config.vdf',
                 'system.reg', 'user.reg', 'userdef.reg', 'cookies',
                 'cookies-journal', 'login data', '.git-credentials', '.netrc'}
SECRET_PATTERNS = [
    re.compile(rb'gh[pousr]_[A-Za-z0-9]{36,}'),
    re.compile(rb'github_pat_[A-Za-z0-9_]{30,}'),
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(rb'"(?:AccountName|AutoLoginUser|RefreshToken)"\s*"[^"\r\n]+"', re.I),
]


def check_path(name):
    path = PurePosixPath(name)
    parts = {part.lower() for part in path.parts}
    base = path.name.lower()
    if (path.is_absolute() or '..' in parts or parts & PRIVATE_DIRS
            or base in PRIVATE_FILES or base.startswith('.env')
            or re.fullmatch(r'ssfn\d+', base)):
        raise RuntimeError('Private account/runtime path: ' + name)


def check_content(name, data):
    if any(pattern.search(data) for pattern in SECRET_PATTERNS):
        raise RuntimeError('Possible credential in: ' + name)


def check_bundle(root):
    for path in root.rglob('*'):
        name = path.relative_to(root).as_posix()
        check_path(name)
        if path.is_symlink():
            raise RuntimeError('Unexpected bundle symlink: ' + name)
        if path.is_file():
            check_content(name, path.read_bytes())


def check_git(root, history=False):
    # Only examine Git objects/index; never read the user's live Steam profile.
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args])
    from distribution import ROOT_FILES, EXTRA, TREES
    seen = set()
    def inspect(mode, oid, name):
        check_path(name)
        path = PurePosixPath(name)
        allowed = (name in ROOT_FILES | EXTRA or
                   (len(path.parts) > 1 and path.parts[0] in TREES and
                    path.suffix in TREES[path.parts[0]] and '__pycache__' not in path.parts))
        if not allowed or mode not in ('100644', '100755'):
            raise RuntimeError('Unapproved source entry: ' + name)
        if oid not in seen:
            check_content(name, git('cat-file', 'blob', oid))
            seen.add(oid)
    for record in git('ls-files', '--stage', '-z').split(b'\0'):
        if not record:
            continue
        meta, name = record.split(b'\t', 1)
        mode, oid, stage = meta.decode().split()
        if stage != '0':
            raise RuntimeError('Resolve Git conflicts before auditing')
        inspect(mode, oid, name.decode())
    if history:
        for commit in git('rev-list', '--all').decode().splitlines():
            for record in git('ls-tree', '-rz', commit).split(b'\0'):
                if not record:
                    continue
                meta, name = record.split(b'\t', 1)
                mode, kind, oid = meta.decode().split()
                inspect(mode, oid, name.decode())
    return len(seen)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true')
    args = parser.parse_args()
    count = check_git(Path(__file__).resolve().parents[1], args.history)
    print(f'Privacy check passed: {count} unique source blobs; no known account files or credential patterns.')


if __name__ == '__main__':
    main()

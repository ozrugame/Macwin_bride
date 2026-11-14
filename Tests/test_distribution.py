import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/distribution.py'
spec=importlib.util.spec_from_file_location('distribution',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class DistributionTests(unittest.TestCase):
    def test_source_export_never_copies_private_runtime_or_local_history(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'source';out=Path(d)/'out';root.mkdir()
            paths=['Package.swift','README.md','scripts/steam_session.py','Sources/App/main.swift',
                   'var/Steam/config/loginusers.vdf','.runtime/wine','dist/App.app/secret',
                   'docs/progress.md','scripts/__pycache__/test.pyc','.env',
                   'docs/BUILD.md','third_party/steam-webhelper/LICENSE']
            for name in paths:
                f=root/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('fixture')
            m.export_source(root,out)
            exported={str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}
            self.assertEqual(exported,{'Package.swift','README.md','scripts/steam_session.py',
                'Sources/App/main.swift','docs/BUILD.md','third_party/steam-webhelper/LICENSE'})

    def test_export_rejects_symlinks_into_user_data(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'source';out=Path(d)/'out';(root/'scripts').mkdir(parents=True)
            private=Path(d)/'private';private.write_text('secret')
            (root/'scripts/leak.py').symlink_to(private)
            with self.assertRaises(RuntimeError):m.export_source(root,out)

    def test_pruning_swift_build_symlink_keeps_its_target_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);stage=root/'bundle';build=stage/'.build';build.mkdir(parents=True)
            outside=root/'keep';outside.mkdir();(outside/'important').write_text('keep')
            (build/'release').symlink_to(outside,target_is_directory=True)
            for folder,name in [('webhelper','steamwebhelper.exe'),('steam-session','steam-window-watch.exe')]:
                (build/folder).mkdir();(build/folder/name).write_bytes(b'PE fixture')
                (build/folder/'cache').mkdir()
            m.prune_build(stage)
            self.assertFalse((build/'release').is_symlink())
            self.assertEqual((outside/'important').read_text(),'keep')
            self.assertEqual(sorted(str(f.relative_to(build)) for f in build.rglob('*') if f.is_file()),
                ['steam-session/steam-window-watch.exe','webhelper/steamwebhelper.exe'])

if __name__=='__main__':unittest.main()

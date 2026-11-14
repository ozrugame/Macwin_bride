import importlib.util
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class SharedStorageTests(unittest.TestCase):
    def setup_layout(self, r):
        old=r/'var/prefixes/world/drive_c/Program Files (x86)/Steam/steamapps'
        active=r/'var/prefixes/limbus-dxmt/drive_c/Program Files (x86)/Steam'
        for p,data in [(old/'downloading/582010/chunk.bin',b'partial download'),(old/'appmanifest_582010.acf',b'paused-manifest'),(active/'Steam.exe',b'steam'),(active/'steamapps/common/Limbus Company/LimbusCompany.exe',b'game'),(active/'steamapps/appmanifest_1973530.acf',b'current manifest'),(r/'var/prefixes/limbus-dxmt/system.reg',b'registry')]:
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        return old,active
    def test_moves_existing_files_once_and_reuses_library(self):
        m=module('shared_storage')
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);old,active=self.setup_layout(r)
            inode=(old/'downloading/582010/chunk.bin').stat().st_ino
            m.migrate(r)
            central=r/'var/Steam/steamapps'
            self.assertEqual((central/'downloading/582010/chunk.bin').stat().st_ino,inode)
            self.assertEqual((central/'appmanifest_582010.acf').read_bytes(),b'paused-manifest')
            link=r/'var/prefixes/shared/drive_c/Program Files (x86)/Steam'
            self.assertTrue(link.is_symlink())
            self.assertEqual((link/'Steam.exe').read_bytes(),b'steam')
            self.assertEqual((central/'common/Limbus Company/LimbusCompany.exe').read_bytes(),b'game')
            m.migrate(r) # repeated request performs no copy
            self.assertEqual((central/'downloading/582010/chunk.bin').stat().st_ino,inode)
    def test_destination_conflict_never_overwrites_data(self):
        m=module('shared_storage')
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);old,active=self.setup_layout(r)
            (r/'var/Steam').mkdir()
            with self.assertRaises(RuntimeError):m.migrate(r)
            self.assertEqual((old/'downloading/582010/chunk.bin').read_bytes(),b'partial download')
            self.assertTrue((active/'Steam.exe').is_file())
    def test_failed_move_rolls_back_prior_moves(self):
        m=module('shared_storage')
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);old,active=self.setup_layout(r)
            real=m.os.rename;calls=0
            def failing(a,b):
                nonlocal calls
                calls+=1
                if calls==3:raise OSError('simulated failure')
                return real(a,b)
            with patch.object(m.os,'rename',side_effect=failing):
                with self.assertRaises(OSError):m.migrate(r)
            self.assertTrue((active/'Steam.exe').is_file())
            self.assertTrue((old/'downloading/582010/chunk.bin').is_file())
            self.assertFalse((r/'var/prefixes/shared').exists())
    def test_migration_with_user_deleted_world_does_not_recreate_it(self):
        import shutil
        m=module('shared_storage')
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);old,active=self.setup_layout(r)
            shutil.rmtree(r/'var/prefixes/world')
            m.migrate(r)
            self.assertFalse((r/'var/prefixes/world').exists())
            self.assertTrue((r/'var/Steam/Steam.exe').exists())

    def test_maintenance_blocks_launch_without_starting_wine(self):
        import fcntl, sys
        m=module('steam_session');storage=module('shared_storage')
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'var').mkdir()
            with open(r/'var/steam-maintenance.lock','a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(m,'__file__',str(r/'scripts/steam_session.py')), patch.object(m.sys,'argv',['steam_session.py']), patch.dict(sys.modules,{'shared_storage':storage}), patch.object(m,'run_session') as run:
                    with self.assertRaises(RuntimeError):m.main()
                    run.assert_not_called()

    def test_routing_selects_app_without_another_prefix(self):
        m=module('steam_session')
        self.assertEqual(m.steam_arguments(['wine','Steam.exe','-noverifyfiles'],['--install-app','582010']),['wine','Steam.exe','-noverifyfiles','steam://install/582010'])
        self.assertEqual(m.steam_arguments(['wine','Steam.exe','-noverifyfiles'],['--app-id','1446780']),['wine','Steam.exe','-noverifyfiles','-applaunch','1446780'])
        self.assertIn('-video-allow-hw-acceleration',m.steam_arguments(['wine','Steam.exe','-noverifyfiles'],['--limbus']))
        with self.assertRaises(SystemExit):m.steam_arguments(['wine','Steam.exe'],['--app-id','bad'])

if __name__=='__main__':unittest.main()

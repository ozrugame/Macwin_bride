import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'scripts/steam_session.py'

class ShutdownTests(unittest.TestCase):
    def load(self):
        self.assertTrue(MODULE.exists(), 'Managed session implementation is missing')
        spec = importlib.util.spec_from_file_location('steam_session', MODULE)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        return m

    def test_shutdown_tries_graceful_then_scoped_server_and_verifies(self):
        m = self.load(); calls=[]
        def run(args, **kwargs):
            import subprocess
            calls.append((args, kwargs['env']['WINEPREFIX']))
            if args[-1]=='-w' and sum(a[-1]=='-w' for a,p in calls)==1:
                raise subprocess.TimeoutExpired(args, 0.01)
            return subprocess.CompletedProcess(args,0)
        with patch.object(m.subprocess,'run', side_effect=run):
            m.shutdown(Path('/runtime/bin/wine'),Path('/prefix/Steam.exe'),{'WINEPREFIX':'/prefix'},grace=0.01)
        self.assertEqual([a[0][-1] for a in calls],['-shutdown','-s','-w','-k','-w'])
        self.assertTrue(all(p=='/prefix' for a,p in calls))

    def test_unverifiable_cleanup_is_an_error(self):
        m=self.load()
        import subprocess
        with patch.object(m.subprocess,'run', return_value=subprocess.CompletedProcess([],7)):
            with self.assertRaises(RuntimeError):
                m.shutdown(Path('/runtime/bin/wine'),Path('/prefix/Steam.exe'),{'WINEPREFIX':'/prefix'},grace=0.01)

class LaunchOptionsTests(unittest.TestCase):
    def test_existing_options_preserved_and_only_limbus_changes(self):
        spec=importlib.util.spec_from_file_location('steam_session',MODULE)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        self.assertTrue(hasattr(m,'limbus_launch_options'),'Persistent Steam launch options missing')
        source='"apps" { "123" { "LaunchOptions" "keep" } "1973530" { "LaunchOptions" "-screen-fullscreen 0 -video-allow-hw-acceleration 1" } }'
        result=m.limbus_launch_options(source)
        self.assertIn('"LaunchOptions" "keep"',result)
        self.assertIn('-screen-fullscreen 0 -video-allow-hw-acceleration 0',result)
        self.assertEqual(m.limbus_launch_options(result),result)
    def test_missing_game_block_fails_without_modification(self):
        spec=importlib.util.spec_from_file_location('steam_session',MODULE)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        self.assertTrue(hasattr(m,'limbus_launch_options'),'Persistent Steam launch options missing')
        with self.assertRaises(RuntimeError):m.limbus_launch_options('"apps" { "123" {} }')

class SessionOwnershipTests(unittest.TestCase):
    def fixture(self, root):
        import shutil
        project=Path(root)
        (project/'scripts').mkdir()
        shutil.copy2(MODULE.parent/'launch-limbus.py', project/'scripts/launch-limbus.py')
        wine=project/'.runtime/sikarugir/wswine.bundle/bin/wine'
        for item in [wine, wine.parent/'wineserver', project/'var/prefixes/shared/system.reg',
                     project/'var/Steam/Steam.exe', project/'.runtime/gstreamer-video-plugins/libgstlibav.dylib',
                     project/'.build/steam-session/steam-window-watch.exe']:
            item.parent.mkdir(parents=True, exist_ok=True); item.touch()
        link=project/'var/prefixes/shared/drive_c/Program Files (x86)/Steam'
        link.parent.mkdir(parents=True); link.symlink_to(project/'var/Steam')
        return project

    def load(self):
        import sys
        sys.path.insert(0,str(MODULE.parent))
        spec=importlib.util.spec_from_file_location('session_test', MODULE)
        m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        return m

    def test_second_icon_during_update_does_not_launch_another_steam(self):
        import tempfile, fcntl
        m=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(d)
            with (p/'var/steam-session.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(m,'__file__',str(p/'scripts/steam_session.py')), patch.object(m.sys,'argv',['steam_session.py']), patch.object(m.signal,'signal'), patch.object(m.subprocess,'Popen') as launch:
                    self.assertEqual(m.run_session(),0)
                    launch.assert_not_called()

    def test_busy_unmanaged_prefix_with_changed_helper_is_not_shutdown(self):
        import tempfile, steam_update
        m=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(d)
            with patch.object(m,'__file__',str(p/'scripts/steam_session.py')), patch.object(m.sys,'argv',['steam_session.py']), patch.object(m.signal,'signal'), patch.object(steam_update,'prefix_idle',return_value=False), patch.object(m,'shutdown') as shutdown, patch.object(steam_update,'update_client') as updater:
                with self.assertRaises(RuntimeError): m.run_session()
                shutdown.assert_not_called(); updater.assert_not_called()

if __name__=='__main__': unittest.main()

import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import threading
import subprocess
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import steam_update as m


def pe(payload):
    data = bytearray(128)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 80)
    data[80:86] = b'PE\0\0\x64\x86'
    return bytes(data) + payload


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.steam = self.project / 'var/Steam'
        self.folder = self.steam / 'bin/cef/cef.win64'; self.folder.mkdir(parents=True)
        self.wrapper = pe(b'wrapper'); self.old = pe(b'old'); self.new = pe(b'new official')
        self.built = self.project / '.build/webhelper/steamwebhelper.exe'
        self.built.parent.mkdir(parents=True); self.built.write_bytes(self.wrapper)
        self.helper = self.folder / 'steamwebhelper.exe'; self.helper.write_bytes(self.wrapper)
        self.real = self.folder / 'steamwebhelper_real.exe'; self.real.write_bytes(self.old)
        self.marker = self.steam / '.macwin-webhelper.json'
        self.marker.write_text(json.dumps(dict(wrapperSHA256=m.digest(self.wrapper), originalSHA256=m.digest(self.old), clientBuild='1', sourceCommit='preserve')))
        self.package = self.steam / 'package'; self.package.mkdir()
        self.install(self.old, '1')

    def install(self, data, version):
        (self.package / 'steam_client_win64.installed').write_text('bin\\cef\\cef.win64\\steamwebhelper.exe,%d;123;%d\n' % (len(data), zlib.crc32(data)))
        (self.package / 'steam_client_win64.manifest').write_text('"win64" { "version" "%s" }' % version)

    def test_same_build_replaced_wrapper_repairs_without_copying_games(self):
        self.helper.write_bytes(self.old)
        self.assertTrue(m.repair(self.project, self.steam))
        self.assertEqual(self.helper.read_bytes(), self.wrapper)
        self.assertEqual(self.real.read_bytes(), self.old)
        m.validate(self.steam)

    def test_updated_helper_is_preserved_as_real_and_marker_is_updated(self):
        self.helper.write_bytes(self.new); self.install(self.new, '2')
        m.repair(self.project, self.steam)
        self.assertEqual(self.real.read_bytes(), self.new)
        record = json.loads(self.marker.read_text())
        self.assertEqual(record['clientBuild'], '2')
        self.assertEqual(record['sourceCommit'], 'preserve')
        m.validate(self.steam)

    def test_healthy_is_noop_even_without_build_artifact(self):
        self.built.unlink(); before = self.helper.stat().st_mtime_ns
        self.assertFalse(m.repair(self.project, self.steam))
        self.assertEqual(self.helper.stat().st_mtime_ns, before)

    def test_corrupt_candidate_or_build_never_overwrites_files(self):
        for target in (self.helper, self.built):
            self.helper.write_bytes(self.new); self.built.write_bytes(self.wrapper)
            self.install(self.new, '2'); target.write_bytes(b'broken')
            before = [p.read_bytes() for p in (self.helper, self.real, self.marker)]
            with self.assertRaises(RuntimeError): m.repair(self.project, self.steam)
            self.assertEqual([p.read_bytes() for p in (self.helper, self.real, self.marker)], before)

    def test_restart_after_marker_write_failure_recovers_from_new_real(self):
        self.helper.write_bytes(self.new); self.install(self.new, '2')
        original = m.atomic_write
        def interrupted(path, data):
            if path == self.marker: raise OSError('simulated power loss')
            original(path, data)
        with patch.object(m, 'atomic_write', side_effect=interrupted):
            with self.assertRaises(OSError): m.repair(self.project, self.steam)
        self.assertEqual(self.helper.read_bytes(), self.wrapper)
        self.assertEqual(self.real.read_bytes(), self.new)
        m.repair(self.project, self.steam); m.validate(self.steam)

    def test_startup_repairs_after_updater_overwrites_wrapper(self):
        def updater(*args):
            self.helper.write_bytes(self.new); self.install(self.new, '2')
        with patch.object(m, 'prefix_idle', return_value=True), patch.object(m, 'update_client', side_effect=updater) as update:
            m.initialize_client(self.project, self.steam, Path('/wine/bin/wine'), {}, None, threading.Event())
        update.assert_called_once()
        m.validate(self.steam)
        self.assertEqual(self.real.read_bytes(), self.new)

    def test_running_prefix_never_updates_or_repairs(self):
        self.helper.write_bytes(self.new)
        with patch.object(m, 'prefix_idle', return_value=False), patch.object(m, 'update_client') as update, patch.object(m, 'repair') as repair:
            with self.assertRaises(RuntimeError):
                m.initialize_client(self.project, self.steam, Path('/wine/bin/wine'), {}, None, threading.Event())
        update.assert_not_called(); repair.assert_not_called()
        self.assertEqual(self.helper.read_bytes(), self.new)

    def test_updater_failure_never_repairs_partial_download(self):
        before = self.marker.read_bytes()
        with patch.object(m, 'prefix_idle', return_value=True), patch.object(m, 'update_client', side_effect=RuntimeError('network failed')), patch.object(m, 'repair') as repair:
            with self.assertRaises(RuntimeError):
                m.initialize_client(self.project, self.steam, Path('/wine/bin/wine'), {}, None, threading.Event())
        repair.assert_not_called(); self.assertEqual(self.marker.read_bytes(), before)

    def test_pending_zzz_settings_recover_before_steam_update(self):
        import zzz_session
        calls=[]
        with patch.object(m,'prefix_idle',return_value=True), patch.object(zzz_session,'recover',side_effect=lambda root:calls.append(('recover',root))), patch.object(m,'update_client',side_effect=lambda *args:calls.append(('update',None))):
            m.initialize_client(self.project,self.steam,Path('/wine/bin/wine'),{},None,threading.Event())
        self.assertEqual(calls,[('recover',self.steam.resolve().parent),('update',None)])

    def test_unregistered_wrapper_is_never_silently_installed(self):
        self.marker.write_text('broken')
        with self.assertRaises(RuntimeError): m.repair(self.project, self.steam)

class IdleProbeTests(unittest.TestCase):
    def test_idle_server_can_take_a_second_to_start_and_exit_on_macos(self):
        with tempfile.TemporaryDirectory() as d:
            server=Path(d)/'wineserver'
            server.write_text('#!'+sys.executable+'\nimport time\ntime.sleep(0.8)\n')
            server.chmod(0o755)
            self.assertTrue(m.prefix_idle(Path(d)/'wine',{}))

class UpdaterTests(unittest.TestCase):
    def test_exitsteam_254_requires_fresh_completed_update_log(self):
        from unittest.mock import Mock
        for fresh, good in [('[x] Nothing to do\n[x] Shutdown\n', True),
                            ('[x] Update complete, launching Steam...\n[x] Shutdown\n', True),
                            ('[x] Fatal Error: network\n[x] Shutdown\n', False), ('', False)]:
            with self.subTest(fresh=fresh), tempfile.TemporaryDirectory() as d:
                steam = Path(d); bootstrap = steam / 'logs/bootstrap_log.txt'
                bootstrap.parent.mkdir(); bootstrap.write_text('[old] Nothing to do\n[old] Shutdown\n')
                child = Mock(); child.poll.return_value = 254; child.returncode = 254
                def launch(*args, **kwargs):
                    with bootstrap.open('a') as f: f.write(fresh)
                    return child
                with patch.object(m.subprocess, 'Popen', side_effect=launch), patch.object(m.subprocess, 'run') as wait:
                    if good:
                        m.update_client(Path('/wine/bin/wine'), steam, {}, None, threading.Event())
                        wait.assert_called_once()
                    else:
                        with self.assertRaises(RuntimeError):
                            m.update_client(Path('/wine/bin/wine'), steam, {}, None, threading.Event())
                        wait.assert_not_called()

if __name__ == '__main__': unittest.main()

import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import zzz_session as m

class ZZZSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name);self.root=self.project/'var'
        self.game,self.system,self.journal=m.paths(self.root)
        self.game.mkdir(parents=True);self.system.mkdir(parents=True)
        self.config=self.game/'config.ini'
        self.original=b'[General]\r\nchannel=1\r\nsub_channel=5\r\ncps=Steam\r\ngame_version=3.3.0\r\n[Other]\r\ncps=untouched\r\n'
        self.config.write_bytes(self.original)
        self.support=self.project/'.runtime/zzz-support';self.support.mkdir(parents=True)
        self.specs={}
        for name in ['steam.exe','lsteamclient.dll']:
            data=('test-'+name).encode();(self.support/name).write_bytes(data)
            self.specs[name]=hashlib.sha256(data).hexdigest()
        self.patcher=patch.object(m,'HELPERS',self.specs);self.patcher.start();self.addCleanup(self.patcher.stop)

    def test_login_channel_is_temporary_and_other_settings_are_unchanged(self):
        m.begin(self.project,self.root)
        current=self.config.read_bytes()
        self.assertIn(b'sub_channel=0\r\ncps=mihoyo',current)
        self.assertIn(b'[Other]\r\ncps=untouched',current)
        self.assertEqual((self.system/'steam.exe').read_bytes(),b'test-steam.exe')
        m.recover(self.root)
        self.assertEqual(self.config.read_bytes(),self.original)
        self.assertFalse(self.journal.exists());self.assertFalse((self.system/'steam.exe').exists())
        m.recover(self.root) # safe when Steam's next startup also checks recovery

    def test_existing_helper_is_not_overwritten(self):
        (self.system/'steam.exe').write_bytes(b'existing Wine helper')
        with self.assertRaises(RuntimeError):m.begin(self.project,self.root)
        self.assertEqual(self.config.read_bytes(),self.original);self.assertFalse(self.journal.exists())

    def test_corrupt_source_does_not_change_any_target(self):
        (self.support/'lsteamclient.dll').write_bytes(b'bad')
        with self.assertRaises(RuntimeError):m.begin(self.project,self.root)
        self.assertFalse(self.journal.exists());self.assertEqual(self.config.read_bytes(),self.original)
        self.assertFalse((self.system/'steam.exe').exists())

    def test_interrupted_install_is_recovered_on_next_launch(self):
        write=m.atomic_write
        def fail(path,data):
            if path==self.system/'lsteamclient.dll':raise OSError('interrupted')
            write(path,data)
        with patch.object(m,'atomic_write',side_effect=fail):
            with self.assertRaises(OSError):m.begin(self.project,self.root)
        self.assertTrue(self.journal.exists())
        m.recover(self.root)
        self.assertEqual(self.config.read_bytes(),self.original)
        self.assertFalse((self.system/'steam.exe').exists())

    def test_recovery_refuses_changed_files_without_overwriting_them(self):
        m.begin(self.project,self.root)
        changed=self.config.read_bytes()+b'new-user-data=keep\r\n';self.config.write_bytes(changed)
        with self.assertRaises(RuntimeError):m.recover(self.root)
        self.assertEqual(self.config.read_bytes(),changed);self.assertTrue(self.journal.exists())

    def test_unknown_channel_is_not_silently_changed(self):
        self.config.write_bytes(self.original.replace(b'channel=1',b'channel=9'))
        with self.assertRaises(RuntimeError):m.begin(self.project,self.root)
        self.assertFalse(self.journal.exists())

if __name__=='__main__':unittest.main()

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import privacy_check as privacy


class PrivacyTests(unittest.TestCase):
    def test_account_files_are_rejected_outside_the_usual_profile(self):
        for name in ['backup/loginusers.vdf', 'nested/ssfn12345', 'copy/userdata/save',
                     'dist/App.app/Contents/Resources/user.reg', '.env.local',
                     'Cookies', '../outside', '/absolute']:
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                privacy.check_path(name)

    def test_credentials_are_rejected_without_echoing_values(self):
        for data in [b'ghp_' + b'a' * 36,
                     b'"Account' + b'Name" "example-user"',
                     b'-----BEGIN ' + b'PRIVATE KEY-----']:
            with self.assertRaises(RuntimeError) as error:
                privacy.check_content('scripts/example.py', data)
            self.assertNotIn(data.decode(), str(error.exception))

    def test_normal_source_is_allowed(self):
        privacy.check_path('Sources/BridgeCore/Configuration.swift')
        privacy.check_content('README.md', b'Log in with your own Steam account.')

    def test_bundle_rejects_credentials_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'README.md').write_text('Source only')
            privacy.check_bundle(root)
            (root / 'copy').symlink_to(root / 'README.md')
            with self.assertRaises(RuntimeError):
                privacy.check_bundle(root)
            (root / 'copy').unlink()
            (root / 'loginusers.vdf').write_text('fixture')
            with self.assertRaises(RuntimeError):
                privacy.check_bundle(root)

    def test_history_detects_account_file_even_after_it_is_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.run(['git', '-C', str(root), *args], check=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git('init')
            git('config', 'user.name', 'Test')
            git('config', 'user.email', 'test@example.invalid')
            (root / 'loginusers.vdf').write_text('fixture')
            git('add', '.')
            git('commit', '-m', 'Fixture account file')
            git('rm', 'loginusers.vdf')
            (root / 'README.md').write_text('clean')
            git('add', '.')
            git('commit', '-m', 'Remove fixture')
            privacy.check_git(root)
            with self.assertRaises(RuntimeError):
                privacy.check_git(root, history=True)


if __name__ == '__main__':
    unittest.main()

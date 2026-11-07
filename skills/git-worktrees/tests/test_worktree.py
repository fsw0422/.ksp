"""Tests for scripts/worktree.py, on throwaway repositories.

Run: python3 -m unittest discover -s <this skill's folder>/tests
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'worktree.py'
# Ignore the user's git config, such as commit signing, and give commits an author.
GIT_ENV = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_AUTHOR_NAME': 'Test', 'GIT_AUTHOR_EMAIL': 'test@example.com',
           'GIT_COMMITTER_NAME': 'Test', 'GIT_COMMITTER_EMAIL': 'test@example.com'}


def git(cwd, *args):
    return subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True,
                          env=GIT_ENV, check=True).stdout.strip()


class WorktreeScriptTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.repo = self.root / 'app'
        self.repo.mkdir()
        git(self.repo, 'init', '-q', '-b', 'main')
        (self.repo / 'README.md').write_text('app\n')
        git(self.repo, 'add', 'README.md')
        git(self.repo, 'commit', '-q', '-m', 'Start')
        env = self.repo / '.env'
        env.write_text('TOKEN=secret\n')
        env.chmod(0o600)
        self.workspace = self.root / 'demo.code-workspace'
        self.write_workspace(['app', 'zeta'])

    def write_workspace(self, paths):
        data = {'folders': [{'path': path} for path in paths], 'settings': {'editor.tabSize': 2}}
        self.workspace.write_text(json.dumps(data, indent='\t') + '\n')

    def workspace_paths(self):
        return [entry['path'] for entry in json.loads(self.workspace.read_text())['folders']]

    def run_script(self, *args):
        return subprocess.run([sys.executable, '-I', str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, env=GIT_ENV)

    def test_add_puts_the_worktree_beside_the_main_checkout(self):
        result = self.run_script('add', self.repo, 'fix/login')
        self.assertEqual(result.returncode, 0, result.stderr)
        folder = self.root / 'app-fix-login'
        self.assertEqual(git(folder, 'branch', '--show-current'), 'fix/login')
        self.assertEqual((folder / '.env').stat().st_mode & 0o777, 0o600)
        self.assertNotIn('TOKEN', result.stdout)
        git(folder, 'check-ignore', '-q', '.env')  # fails if Git could commit the .env
        self.assertEqual(self.workspace_paths(), ['app', 'app-fix-login', 'zeta'])
        self.assertIn('\n\t"folders"', self.workspace.read_text())

    def test_remove_drops_the_worktree_and_its_entry_but_keeps_the_branch(self):
        self.run_script('add', self.repo, 'fix/login')
        result = self.run_script('remove', self.root / 'app-fix-login')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / 'app-fix-login').exists())
        self.assertEqual(self.workspace_paths(), ['app', 'zeta'])
        git(self.repo, 'show-ref', '--verify', '--quiet', 'refs/heads/fix/login')

    def test_existing_branch_without_env(self):
        git(self.repo, 'branch', 'old-work')
        (self.repo / '.env').unlink()
        result = self.run_script('add', self.repo, 'old-work')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('on existing branch old-work', result.stdout)
        self.assertIn('.env: skipped', result.stdout)

    def test_branch_only_on_the_remote_is_tracked(self):
        remote = self.root / 'origin.git'
        git(self.root, 'init', '-q', '--bare', str(remote))
        git(self.repo, 'remote', 'add', 'origin', str(remote))
        git(self.repo, 'push', '-q', 'origin', 'main:shared')
        result = self.run_script('add', self.repo, 'shared')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('tracking origin/shared', result.stdout)
        self.assertEqual(git(self.root / 'app-shared', 'rev-parse', '--abbrev-ref', '@{upstream}'), 'origin/shared')

    def test_new_branch_takes_env_from_the_checkout_of_its_start(self):
        self.run_script('add', self.repo, 'parent')
        (self.root / 'app-parent' / '.env').write_text('FROM=parent\n')
        result = self.run_script('add', self.repo, 'parent-child', '--from', 'parent')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / 'app-parent-child' / '.env').read_text(), 'FROM=parent\n')

    def test_workspace_with_comments_is_left_for_a_manual_edit(self):
        text = '{\n\t// my folders\n\t"folders": [{"path": "app"}]\n}\n'
        self.workspace.write_text(text)
        result = self.run_script('add', self.repo, 'feature')
        self.assertEqual(result.returncode, 1)
        self.assertIn('update it by hand', result.stdout)
        self.assertEqual(self.workspace.read_text(), text)
        self.assertTrue((self.root / 'app-feature').is_dir())

    def test_workspace_without_the_main_checkout_is_untouched(self):
        self.write_workspace(['other'])
        before = self.workspace.read_text()
        result = self.run_script('add', self.repo, 'feature')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.workspace.read_text(), before)
        self.assertIn('no .code-workspace file', result.stdout)

    def test_refuses_an_existing_folder(self):
        (self.root / 'app-feature').mkdir()
        result = self.run_script('add', self.repo, 'feature')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already exists', result.stderr)


if __name__ == '__main__':
    unittest.main()

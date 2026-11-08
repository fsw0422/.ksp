"""Shared test helpers: git in throwaway repositories, and running the script."""
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


def git_maybe(cwd, *args):
    """Run git and return its output, or None if it fails."""
    result = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True, env=GIT_ENV)
    return result.stdout.strip() if result.returncode == 0 else None


def run_script(*args):
    return subprocess.run([sys.executable, '-I', str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True, env=GIT_ENV)


def commit(folder, name, text, message):
    """Write the file, commit it, and return the new commit."""
    (Path(folder) / name).write_text(text)
    git(folder, 'add', name)
    git(folder, 'commit', '-q', '-m', message)
    return git(folder, 'rev-parse', 'HEAD')


class RepoTest(unittest.TestCase):
    """A throwaway repository, app, with one commit on main."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.repo = self.root / 'app'
        self.repo.mkdir()
        git(self.repo, 'init', '-q', '-b', 'main')
        commit(self.repo, 'README.md', 'one\ntwo\nthree\n', 'Start')

    def add(self, branch, parent):
        result = run_script('add', self.repo, branch, '--from', parent)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.root / f'app-{branch}'

    def sync(self, expected_code=0):
        result = run_script('sync', self.repo)
        self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
        return result.stdout

    def subjects(self, ref):
        return git(self.repo, 'log', '--format=%s', ref).splitlines()

    def squash_into_main(self, branch):
        git(self.repo, 'merge', '--squash', branch)
        git(self.repo, 'commit', '-q', '-m', f'Squash {branch}')

    def add_remote(self):
        """Give the repository an origin, with main pushed to it."""
        self.remote = self.root / 'origin.git'
        git(self.root, 'init', '-q', '--bare', '-b', 'main', str(self.remote))
        git(self.repo, 'remote', 'add', 'origin', str(self.remote))
        git(self.repo, 'push', '-q', '-u', 'origin', 'main')

    def on_remote(self, branch):
        return git_maybe(self.remote, 'rev-parse', '--verify', '--quiet', f'refs/heads/{branch}')

    def teammate(self, branch):
        """Clone the remote's branch, as a teammate's own checkout."""
        other = self.root / 'teammate'
        git(self.root, 'clone', '-q', '-b', branch, str(self.remote), str(other))
        return other

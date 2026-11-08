"""Shared test helpers: git in throwaway repositories, a stand-in for gh, and running the script."""
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

# A stand-in for `gh pr list`. It logs each call, fails when told to, and otherwise prints the pull
# requests saved in head.json or base.json, keeping those listed in the repository it was asked about.
FAKE_GH = '''
import json, os, sys
folder = os.environ['FAKE_GH_DIR']
with open(os.path.join(folder, 'calls'), 'a') as log:
    log.write(' '.join(sys.argv[1:]) + '\\n')
failure = os.path.join(folder, 'failure')
if os.path.exists(failure):
    sys.exit(open(failure).read())
args = sys.argv[1:]
saved = os.path.join(folder, 'head.json' if '--head' in args else 'base.json')
place = args[args.index('--repo') + 1]
found = json.load(open(saved)) if os.path.exists(saved) else []
print(json.dumps([pr for pr in found if pr.pop('in') == place]))
'''


def git(cwd, *args):
    return subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True,
                          env=GIT_ENV, check=True).stdout.strip()


def git_maybe(cwd, *args):
    """Run git and return its output, or None if it fails."""
    result = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True, env=GIT_ENV)
    return result.stdout.strip() if result.returncode == 0 else None


def run_script(*args, env=GIT_ENV):
    return subprocess.run([sys.executable, '-I', str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True, env=env)


def commit(folder, name, text, message):
    """Write the file, commit it, and return the new commit."""
    (Path(folder) / name).write_text(text)
    git(folder, 'add', name)
    git(folder, 'commit', '-q', '-m', message)
    return git(folder, 'rev-parse', 'HEAD')


def pull_request(number, title, head='test/app', listed_in='test/app'):
    """An open pull request as gh lists it, from the head repository, listed in another one."""
    owner, name = head.split('/')
    return {'number': number, 'title': title, 'url': f'https://github.com/{listed_in}/pull/{number}',
            'headRepository': {'name': name}, 'headRepositoryOwner': {'login': owner},
            'in': f'github.com/{listed_in}'}


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

    def add_remote(self, name='origin', address='https://github.com/test/app.git'):
        """Give the repository a remote with main pushed to it.

        Its address looks like GitHub, and an `insteadOf` rule sends every fetch and push to a
        bare repository in the test folder instead.
        """
        bare = self.root / f'{name}.git'
        git(self.root, 'init', '-q', '--bare', '-b', 'main', str(bare))
        git(self.repo, 'remote', 'add', name, address)
        git(self.repo, 'config', f'url.{bare}.insteadOf', address)
        git(self.repo, 'push', '-q', '-u', name, 'main')
        if name == 'origin':
            self.remote = bare
        return bare

    def on_remote(self, branch, bare=None):
        return git_maybe(bare or self.remote, 'rev-parse', '--verify', '--quiet', f'refs/heads/{branch}')

    def teammate(self, branch):
        """Clone the remote's branch, as a teammate's own checkout."""
        other = self.root / 'teammate'
        git(self.root, 'clone', '-q', '-b', branch, str(self.remote), str(other))
        return other


class RemoteTest(RepoTest):
    """A repository with an origin, and a stand-in for gh on the PATH that remove uses."""

    def setUp(self):
        super().setUp()
        self.add_remote()
        self.gh_dir = self.root / 'gh'
        (self.gh_dir / 'bin').mkdir(parents=True)
        fake = self.gh_dir / 'bin' / 'gh'
        fake.write_text(f'#!{sys.executable}\n{FAKE_GH}')
        fake.chmod(0o755)
        self.env = {**GIT_ENV, 'PATH': f'{fake.parent}{os.pathsep}{os.environ["PATH"]}',
                    'FAKE_GH_DIR': str(self.gh_dir)}

    def script(self, *args):
        return run_script(*args, env=self.env)

    def pull_requests(self, kind, *found):
        """Make gh list these open pull requests for --head (kind 'head') or --base (kind 'base')."""
        (self.gh_dir / f'{kind}.json').write_text(json.dumps(found))

    def gh_fails(self, message):
        (self.gh_dir / 'failure').write_text(message)

    def gh_calls(self):
        calls = self.gh_dir / 'calls'
        return calls.read_text().splitlines() if calls.exists() else []

    def publish(self, branch, parent='main'):
        """Create the branch with one commit, and push it, so it has a copy on the remote."""
        folder = self.add(branch, parent)
        commit(folder, f'{branch}.txt', f'{branch}\n', f'Add {branch}')
        git(folder, 'push', '-q', '-u', 'origin', branch)
        return folder

    def local(self, branch):
        return git_maybe(self.repo, 'rev-parse', '--verify', '--quiet', f'refs/heads/{branch}')

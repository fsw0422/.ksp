"""Shared test helpers: git in throwaway repositories, and running the script."""
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'worktree.py'
# Ignore the user's git config, such as commit signing, and give commits an author.
GIT_ENV = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_AUTHOR_NAME': 'Test', 'GIT_AUTHOR_EMAIL': 'test@example.com',
           'GIT_COMMITTER_NAME': 'Test', 'GIT_COMMITTER_EMAIL': 'test@example.com'}


def git(cwd, *args):
    return subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True,
                          env=GIT_ENV, check=True).stdout.strip()


def run_script(*args):
    return subprocess.run([sys.executable, '-I', str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True, env=GIT_ENV)


def commit(folder, name, text, message):
    """Write the file, commit it, and return the new commit."""
    (Path(folder) / name).write_text(text)
    git(folder, 'add', name)
    git(folder, 'commit', '-q', '-m', message)
    return git(folder, 'rev-parse', 'HEAD')

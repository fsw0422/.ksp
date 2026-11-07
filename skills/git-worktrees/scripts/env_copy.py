"""Copy a checkout's .env into a new worktree, without printing it or letting Git commit it."""
import os
from pathlib import Path

from checkouts import git, git_succeeds


def copy_env(source_dir, worktree):
    """Copy source_dir/.env into the worktree with the same permissions. Return what happened."""
    source = Path(source_dir, '.env')
    if not source.is_file():
        return f'skipped, {source_dir} has no .env'
    mode = source.stat().st_mode & 0o777
    target = Path(worktree, '.env')
    try:
        # O_EXCL never overwrites, and the new file is never more open than the source.
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    except FileExistsError:
        return 'skipped, the worktree already has a .env'
    with os.fdopen(fd, 'wb') as out:
        out.write(source.read_bytes())
    os.chmod(target, mode)  # os.open applies the umask, so set the exact mode
    _keep_out_of_git(worktree)
    return f'copied from {source_dir}'


def _keep_out_of_git(worktree):
    """Add a local Git exclusion for .env, unless Git already ignores it."""
    if git_succeeds(worktree, 'check-ignore', '-q', '.env'):
        return
    exclude = Path(worktree, git(worktree, 'rev-parse', '--git-path', 'info/exclude'))
    exclude.parent.mkdir(parents=True, exist_ok=True)
    text = exclude.read_text() if exclude.exists() else ''
    separator = '' if not text or text.endswith('\n') else '\n'
    exclude.write_text(f'{text}{separator}/.env\n')

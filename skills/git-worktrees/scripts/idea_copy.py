"""Copy a checkout's IntelliJ files that Git doesn't track, such as its modules and build settings, into a new worktree."""
import shutil
from pathlib import Path

from checkouts import git_try, keep_out_of_git

# Left out: the checkout's own window and run state, which IntelliJ makes anew, its project name,
# because the worktree goes by its folder's name, and macOS folder settings.
SKIPPED_FILES = {'.idea/workspace.xml', '.idea/.name'}
SKIPPED_NAMES = {'shelf', '.DS_Store'}  # shelved changes stay with the checkout they came from


def copy_idea(source_dir, worktree):
    """Copy the .idea files Git doesn't track in source_dir that the worktree lacks. Return what happened."""
    listed = git_try(source_dir, 'ls-files', '--others', '-z', '--', '.idea') or ''
    names = [name for name in listed.split('\0') if name and _wanted(name)]
    if not names:
        return f"skipped, {source_dir} has no IntelliJ files that Git doesn't track"
    copied = [name for name in names if _copy(Path(source_dir, name), Path(worktree, name))]
    for name in copied:
        keep_out_of_git(worktree, name)
    if not copied:
        return 'skipped, the worktree already has them'
    return f'copied {len(copied)} file{"s" if len(copied) > 1 else ""} from {source_dir}'


def _wanted(name):
    return name not in SKIPPED_FILES and not SKIPPED_NAMES & set(Path(name).parts)


def _copy(source, target):
    """Copy the file unless the target exists. Return True if it copied."""
    if target.exists() or not source.is_file():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True

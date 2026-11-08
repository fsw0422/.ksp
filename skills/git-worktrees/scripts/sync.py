"""Move every child branch onto its parent's head, parents first, at every depth.

A branch is left exactly as it was when a rebase isn't safe: its work is already in the parent,
it has no worktree, its worktree has uncommitted files or a rebase in progress, its copy on the
remote has commits it lacks, or its rebase conflicts. Sync never pushes.
"""
import re
import time
from pathlib import Path

from checkouts import GitError, branch_exists, checkouts, git, git_try, main_checkout
from lineage import base_of, commit_of, parent_links, set_base, walk
from remote_copy import foreign_commits, remote_copy, short_name, update_hint

REBASING = ('rebase-merge', 'rebase-apply')
MERGING = ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD')
RANGE_DIFF_MARK = re.compile(r'^\s*(?:\d+|-):\s+\S+\s+([=!<>])\s', re.M)


def sync(repo):
    """Print the branch tree and what happened to each branch. Return True if none was left behind."""
    links = parent_links(repo)
    if not links:
        print('No branch has a recorded parent yet. Record one with `worktree.py parent <worktree> <parent>`.')
        return True
    print(main_checkout(repo))
    folders = {branch: path for path, branch in checkouts(repo) if branch and path.is_dir()}
    stamp = time.strftime('%Y-%m-%d-%H%M%S')
    walked, left, moved = set(), 0, []
    for branch, parent, depth in walk(links):
        walked.add(branch)
        if parent is None:
            print(f'{branch} {git_try(repo, "rev-parse", "--short", "--verify", "--quiet", branch) or "(no such branch)"}')
            continue
        try:
            state, message = follow(repo, branch, parent, folders.get(branch), stamp)
        except GitError as error:
            state, message = 'left', f'skipped, git: {error}'
        print(f'{"  " * depth}{branch}: {message}')
        left += state == 'left'
        if state == 'moved':
            moved.append(branch)
    looped = sorted(set(links) - walked)
    _print_footer(repo, stamp, moved, looped)
    return not left and not looped


def follow(repo, branch, parent, folder, stamp):
    """Bring the branch onto its parent's head when that's safe. Return (state, message).

    The state is 'current' if it already was there, 'moved' if sync rebased it, or 'left' if it stays behind.
    """
    if not branch_exists(repo, parent):
        return 'left', f'its parent {parent} no longer exists; record a new one with `worktree.py parent`'
    head, tip = commit_of(repo, parent), commit_of(repo, branch)
    base = base_of(repo, branch, parent)
    if base == head:
        set_base(repo, branch, head)
        return 'current', "on its parent's head"
    reason = _unsafe(repo, branch, parent, folder, base, tip)
    if reason:
        return 'left', reason
    git(repo, 'update-ref', f'refs/recovery/sync/{stamp}/tip/{branch}', tip)
    git(repo, 'update-ref', f'refs/recovery/sync/{stamp}/base/{branch}', base)
    stopped = _rebase(folder, head, base)
    if stopped:
        return 'left', (f'{stopped}, so it was left as it was. To rebase it by hand, '
                        f'run in its worktree: git rebase --onto {parent} {base[:12]}')
    set_base(repo, branch, head)
    return 'moved', f'rebased onto {parent} {head[:7]}: {_summary(repo, base, tip, head, commit_of(repo, branch))}'


def _unsafe(repo, branch, parent, folder, base, tip):
    """Say why the branch can't be rebased now, or return None."""
    if base != tip and _already_in(repo, parent, branch):
        return f'already in {parent}, so it only waits for removal'
    if folder is None:
        return 'behind, but not checked out in any worktree'
    if git(folder, 'status', '--porcelain'):
        return 'behind, but its worktree has uncommitted or untracked files'
    if _in_progress(folder, REBASING + MERGING):
        return 'behind, but a rebase or merge is in progress in its worktree'
    copy = remote_copy(repo, branch)
    foreign = foreign_commits(repo, branch, copy) if copy else 0
    if foreign:
        return f'behind, but {short_name(copy)} has {_commits(foreign)} it lacks; pull them in first'
    return None


def _already_in(repo, parent, branch):
    """True if merging the branch into its parent would change nothing, such as after a squash merge."""
    merged = git_try(repo, 'merge-tree', '--write-tree', parent, branch)
    return merged is not None and merged.splitlines()[0] == git(repo, 'rev-parse', f'{parent}^{{tree}}')


def _in_progress(folder, names):
    return any(Path(folder, git(folder, 'rev-parse', '--git-path', name)).exists() for name in names)


def _rebase(folder, onto, base):
    """Replay the commits after base onto onto. Return None, or why it stopped, after undoing it."""
    try:
        git(folder, 'rebase', '--no-autostash', '--no-update-refs', '--onto', onto, base)
        return None
    except GitError as error:
        reason = str(error).splitlines()[-1]
    if not _in_progress(folder, REBASING):
        return f'its rebase failed ({reason})'
    conflicts = git(folder, 'diff', '--name-only', '--diff-filter=U').split()
    git(folder, 'rebase', '--abort')
    return f'its rebase conflicts in {", ".join(conflicts)}' if conflicts else f'its rebase stopped ({reason})'


def _summary(repo, old_base, old_tip, new_base, new_tip):
    """Describe the branch's own commits after the rebase, as range-diff compares them."""
    if old_base == old_tip:
        return 'it has no commits of its own'
    marks = RANGE_DIFF_MARK.findall(
        git(repo, 'range-diff', '--no-color', f'{old_base}..{old_tip}', f'{new_base}..{new_tip}'))
    changed, dropped = marks.count('!'), marks.count('<')
    words = [f'{_commits(len(marks) - marks.count(">"))} of its own']
    if changed:
        words.append(f'{changed} changed')
    if dropped:
        words.append(f'{dropped} dropped as already in the parent')
    return ', '.join(words if changed or dropped else [*words, 'unchanged'])


def _update_hint(repo, branch):
    copy = remote_copy(repo, branch)
    return update_hint(repo, branch, copy) if copy else None


def _print_footer(repo, stamp, moved, looped):
    if looped:
        print(f'Not synced, because their recorded parents form a loop: {", ".join(looped)}')
    if not moved:
        return
    print(f'Old tips and bases: refs/recovery/sync/{stamp}/')
    hints = [hint for hint in (_update_hint(repo, branch) for branch in moved) if hint]
    if hints:
        print('Copies on the remote, which sync never pushes:')
        for hint in hints:
            print(f'  {hint}')


def _commits(count):
    return f'{count} commit' if count == 1 else f'{count} commits'

"""Delete a removed worktree's branch, here and on its remote, once its parent has all its work."""
import time
from collections import namedtuple

from checkouts import branch_exists, git
from lineage import already_in, parent_links
from pull_requests import UnknownPullRequests, open_pull_requests
from remote_copy import delete, fetch, foreign_commits, remote_copy, short_name, tip_of

# place: where all the branch's work already is, so the branch can go, or None to keep it.
# notes: lines to print. stop: why remove must stop before removing anything, or [] to go on.
Plan = namedtuple('Plan', 'place notes stop')
STOP = 'Stopped before removing anything'


def plan(repo, branch, close_prs=False):
    """Fetch, then decide what remove does with the branch.

    The place is the recorded parent, or the parent's copy on the remote when the branch was merged
    there, such as through a pull request. A branch is kept when it has no recorded parent, when
    other branches build on it, or when it has work neither place has. When the branch can go but
    its copy on the remote can't be deleted safely yet, remove stops, so it can run again later.
    """
    links = parent_links(repo)
    parent = links.get(branch)
    if not parent or not branch_exists(repo, parent):
        return Plan(None, [f'Kept branch {branch}: it has no recorded parent to compare it with.'], [])
    children = sorted(child for child, its_parent in links.items() if its_parent == branch)
    if children:
        return Plan(None, [f'Kept branch {branch}: other branches build on it ({", ".join(children)}).'], [])
    copy, parent_copy = remote_copy(repo, branch), remote_copy(repo, parent)
    notes = fetch(repo, {each.remote for each in (copy, parent_copy) if each})
    remote_parent = short_name(parent_copy) if parent_copy and tip_of(repo, parent_copy) else None
    places = [parent] + ([remote_parent] if remote_parent else [])
    place = next((each for each in places if already_in(repo, each, branch)), None)
    if not place:
        return Plan(None, notes + [f"Kept branch {branch}: it has work that isn't in {' or '.join(places)}."], [])
    if not copy or not tip_of(repo, copy):
        return Plan(place, notes, [])
    stop = _copy_blockers(repo, branch, copy, parent, remote_parent, parent_copy, close_prs)
    return Plan(None if stop else place, notes, stop)


def _copy_blockers(repo, branch, copy, parent, remote_parent, parent_copy, close_prs):
    """Return why the branch's copy on the remote can't be deleted yet, or [] if it can."""
    name = short_name(copy)
    foreign = foreign_commits(repo, branch, copy)
    if foreign:
        return [f"{STOP}: {name} has {foreign} commit{'s' if foreign > 1 else ''} that {branch} doesn't, "
                f'and deleting it would lose them. Pull them in, or delete {name} yourself once they can go.']
    if not remote_parent or not already_in(repo, remote_parent, branch):
        missing = f"{remote_parent} doesn't have its work yet" if remote_parent else f'{parent} has no copy on the remote'
        return [f'{STOP}: {missing}, so deleting {name} would leave that work only on this machine. '
                f'Push {parent}, then run remove again.']
    if close_prs:
        return []
    try:
        found = open_pull_requests(repo, branch, copy, parent_copy)
    except UnknownPullRequests as error:
        return [f"{STOP}: couldn't check the pull requests that use {name}: {error}. "
                'Fix that and run remove again, or add --close-prs to delete it without checking.']
    if not found:
        return []
    return [f'{STOP}: deleting {name} would close the pull requests from it, and close or retarget those into it:',
            *(f'  {line}' for line in found),
            'Merge or close them first, or run remove again with --close-prs.']


def delete_branch(repo, branch, place):
    """Delete the branch here and its copy on the remote, saving its tip first. Return what happened."""
    saved = f'refs/recovery/removed/{time.strftime("%Y-%m-%d-%H%M%S")}/{branch}'
    git(repo, 'update-ref', saved, f'refs/heads/{branch}')
    lines = [f'Deleted branch {branch}: {place} has all its work. Its tip is saved as {saved}.']
    copy = remote_copy(repo, branch)
    if copy:
        lines.append(delete(repo, branch, copy))
    git(repo, 'branch', '--quiet', '-D', branch)
    return lines

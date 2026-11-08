"""Delete a removed worktree's branch, here and on its remote, once its parent has all its work."""
import time

from checkouts import branch_exists, git
from lineage import already_in, parent_links
from remote_copy import delete, fetch, remote_copy, short_name, tip_of


def plan(repo, branch):
    """Fetch, then return (place, notes): where all the branch's work already is, or None to keep it.

    The place is the recorded parent, or the parent's copy on the remote when the branch was merged
    there, such as through a pull request. A branch is kept when it has no recorded parent, when
    other branches build on it, or when it has work neither place has.
    """
    links = parent_links(repo)
    parent = links.get(branch)
    if not parent or not branch_exists(repo, parent):
        return None, [f'Kept branch {branch}: it has no recorded parent to compare it with.']
    children = sorted(child for child, its_parent in links.items() if its_parent == branch)
    if children:
        return None, [f'Kept branch {branch}: other branches build on it ({", ".join(children)}).']
    copies = [copy for copy in (remote_copy(repo, parent), remote_copy(repo, branch)) if copy]
    notes = fetch(repo, {copy.remote for copy in copies})
    places = [parent]
    parent_copy = remote_copy(repo, parent)
    if parent_copy and tip_of(repo, parent_copy):
        places.append(short_name(parent_copy))
    place = next((place for place in places if already_in(repo, place, branch)), None)
    if not place:
        notes.append(f"Kept branch {branch}: it has work that isn't in {' or '.join(places)}.")
    return place, notes


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

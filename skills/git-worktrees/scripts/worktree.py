"""Create, sync and remove git worktrees beside the repository's main checkout.

  python3 worktree.py add <repo> <branch> [--from <parent>] [--env-from <folder>]
  python3 worktree.py sync <repo>
  python3 worktree.py parent <worktree> <parent>
  python3 worktree.py remove <worktree>
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # so `python3 -I` finds the modules beside this file

from checkouts import (GitError, add_worktree, branch_exists, checkout_of, git, main_checkout,  # noqa: E402
                       remote_branch, remove_worktree, sibling_folder)
from env_copy import copy_env  # noqa: E402
from lineage import makes_loop, parent_links, record_parent  # noqa: E402
from remote_copy import remote_copy, short_name  # noqa: E402
from sync import sync  # noqa: E402
from workspace import WorkspaceError, add_folder, remove_folder, workspace_files  # noqa: E402


def add(repo, branch, start, env_from):
    main = main_checkout(repo)
    folder = sibling_folder(main, branch)
    if folder.exists():
        sys.exit(f'{folder} already exists.')
    exists = branch_exists(repo, branch)
    if start and exists:
        sys.exit(f'Branch {branch} already exists, so --from does not apply.')
    if not start and not exists and not remote_branch(repo, branch):
        sys.exit(f'New branch {branch} needs --from <parent>, the branch it builds on.')
    print(f'Created {folder} on {add_worktree(repo, branch, start, folder)}')
    if start:
        print(record_start(repo, branch, start))
    source = env_from or (start and checkout_of(repo, start)) or repo
    print(f'.env: {copy_env(source, folder)}')
    return update_workspaces(main, lambda file: add_folder(file, folder))


def record_start(repo, branch, start):
    """Record start as the new branch's parent when it's a local branch. Return what happened."""
    if not branch_exists(repo, start):
        return f'Parent: none recorded, because {start} is not a local branch, so sync leaves {branch} alone'
    record_parent(repo, branch, start)
    line = f'Parent: {start}, so sync keeps {branch} on its head'
    copy = remote_copy(repo, start)
    behind = int(git(repo, 'rev-list', '--count', f'{start}..{copy}')) if copy else 0
    if behind:
        line += (f'\nNote: {start} is {behind} commit{"s" if behind > 1 else ""} behind {short_name(copy)}, '
                 'as of the last fetch. Pull it, then run sync.')
    return line


def parent(worktree, parent_branch):
    if not worktree.is_dir():
        sys.exit(f'{worktree} does not exist.')
    folder = worktree.resolve()
    branch = git(folder, 'branch', '--show-current')
    if not branch:
        sys.exit(f'{folder} has no branch checked out.')
    if not branch_exists(folder, parent_branch):
        sys.exit(f'{parent_branch} is not a local branch.')
    if makes_loop(parent_links(folder), branch, parent_branch):
        sys.exit(f'{parent_branch} already follows {branch}, so it can\'t be its parent.')
    base = record_parent(folder, branch, parent_branch)
    print(f'Parent of {branch}: {parent_branch}. Its own commits start after {base[:7]}.')
    return True


def remove(worktree):
    if not worktree.is_dir():
        sys.exit(f'{worktree} does not exist. If it was removed by hand, run `git worktree prune` '
                 'in the main checkout and remove its .code-workspace entry yourself.')
    folder = worktree.resolve()
    main = main_checkout(folder)
    if folder == main:
        sys.exit(f'{folder} is the main checkout, not a worktree.')
    remove_worktree(main, folder)
    print(f'Removed {folder}. Its branch is kept.')
    return update_workspaces(main, lambda file: remove_folder(file, folder))


def update_workspaces(main, change):
    """Apply the change to each workspace file that lists the main checkout. Return False if one failed."""
    files = workspace_files(main)
    if not files:
        print('VS Code: no .code-workspace file beside the main checkout lists it')
    ok = True
    for file in files:
        try:
            print(f'{file.name}: {change(file)}')
        except WorkspaceError as error:
            print(f'{file.name}: {error}')
            ok = False
    return ok


def cli():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest='command', required=True)
    add_parser = commands.add_parser('add', help='create a worktree beside the main checkout')
    add_parser.add_argument('repo', type=Path, help='any checkout of the repository')
    add_parser.add_argument('branch')
    add_parser.add_argument('--from', dest='start', help='the branch a new branch builds on, recorded as its parent')
    add_parser.add_argument('--env-from', type=Path, help='checkout to copy .env from')
    sync_parser = commands.add_parser('sync', help="move every child branch onto its parent's head")
    sync_parser.add_argument('repo', type=Path, help='any checkout of the repository')
    parent_parser = commands.add_parser('parent', help="record the branch a worktree's branch builds on")
    parent_parser.add_argument('worktree', type=Path)
    parent_parser.add_argument('parent', help='a local branch')
    remove_parser = commands.add_parser('remove', help='remove a worktree, keeping its branch')
    remove_parser.add_argument('worktree', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'add':
            env_from = args.env_from.resolve() if args.env_from else None
            ok = add(args.repo.resolve(), args.branch, args.start, env_from)
        elif args.command == 'sync':
            ok = sync(args.repo.resolve())
        elif args.command == 'parent':
            ok = parent(args.worktree, args.parent)
        else:
            ok = remove(args.worktree)
    except GitError as error:
        sys.exit(f'git: {error}')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    cli()

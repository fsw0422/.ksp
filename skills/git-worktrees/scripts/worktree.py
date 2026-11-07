"""Create and remove git worktrees beside the repository's main checkout.

  python3 worktree.py add <repo> <branch> [--from <start>] [--env-from <folder>]
  python3 worktree.py remove <worktree>
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # so `python3 -I` finds the modules beside this file

from checkouts import (GitError, add_worktree, branch_exists, checkout_of, main_checkout,  # noqa: E402
                       remove_worktree, sibling_folder)
from env_copy import copy_env  # noqa: E402
from workspace import WorkspaceError, add_folder, remove_folder, workspace_files  # noqa: E402


def add(repo, branch, start, env_from):
    main = main_checkout(repo)
    folder = sibling_folder(main, branch)
    if folder.exists():
        sys.exit(f'{folder} already exists.')
    if start and branch_exists(repo, branch):
        sys.exit(f'Branch {branch} already exists, so --from does not apply.')
    print(f'Created {folder} on {add_worktree(repo, branch, start, folder)}')
    source = env_from or (start and checkout_of(repo, start)) or repo
    print(f'.env: {copy_env(source, folder)}')
    return update_workspaces(main, lambda file: add_folder(file, folder))


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
    add_parser.add_argument('--from', dest='start', help="start of a new branch (default: repo's current commit)")
    add_parser.add_argument('--env-from', type=Path, help='checkout to copy .env from')
    remove_parser = commands.add_parser('remove', help='remove a worktree, keeping its branch')
    remove_parser.add_argument('worktree', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'add':
            env_from = args.env_from.resolve() if args.env_from else None
            ok = add(args.repo.resolve(), args.branch, args.start, env_from)
        else:
            ok = remove(args.worktree)
    except GitError as error:
        sys.exit(f'git: {error}')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    cli()

#!/usr/bin/env python3
"""Create and remove managed worktrees without changing the caller's directory."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


GIT_LOCAL_ENV_VARS = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_OBJECT_DIRECTORY", "GIT_DIR",
    "GIT_WORK_TREE", "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE", "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE", "GIT_PREFIX",
    "GIT_SHALLOW_FILE", "GIT_COMMON_DIR", "GIT_CONFIG",
}


def git_environment() -> dict[str, str]:
    return {
        key: value for key, value in os.environ.items()
        if key.upper() not in GIT_LOCAL_ENV_VARS and not key.upper().startswith("GIT_CONFIG_")
    }


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False,
        env=git_environment(),
    )
    if result.returncode:
        detail = os.fsdecode(result.stderr).strip()
        message = f"git {' '.join(args)} failed (exit {result.returncode})"
        raise ValueError(f"{message}: {detail}" if detail else message)
    return os.fsdecode(result.stdout).strip()


def managed_parent(root: Path) -> Path:
    codex = root.resolve() / ".codex"
    parent = codex / "worktrees"
    if codex.is_symlink() or parent.is_symlink():
        raise ValueError("managed worktree directories must not be symlinks")
    if codex.resolve() != codex or parent.resolve() != parent:
        raise ValueError("managed worktree directories must not resolve to another path")
    return parent


def create(branch: str) -> dict[str, str]:
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel")).resolve()
    if Path.cwd().resolve() != root:
        raise ValueError("run worktree creation from the repository root")
    if branch.startswith("-") or git(root, "check-ref-format", "--branch", branch) != branch:
        raise ValueError(f"invalid literal branch name: {branch}")
    parent = managed_parent(root)
    target = parent / branch.replace("/", "-")
    if target.exists() or target.is_symlink():
        raise ValueError(f"worktree path already exists: {target}")
    existing = subprocess.run(
        ["git", "-C", str(root), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        check=False, env=git_environment(),
    ).returncode == 0
    try:
        if existing:
            git(root, "worktree", "add", "--quiet", "--", str(target), branch)
        else:
            git(root, "worktree", "add", "--quiet", "-b", branch, "--", str(target), "HEAD")
    except (OSError, ValueError) as error:
        cleanup = cleanup_failed_create(root, target, branch)
        raise ValueError(f"{error}; {cleanup}") from error
    return {"main_root": str(root), "worktree_path": str(target), "branch": branch}


def registered_worktrees(root: Path) -> set[Path]:
    return {
        Path(item[9:]).resolve()
        for item in git(root, "worktree", "list", "--porcelain", "-z").split("\0")
        if item.startswith("worktree ")
    }


def cleanup_failed_create(root: Path, target: Path, branch: str) -> str:
    location = f"{target} (branch {branch})"
    try:
        registered = registered_worktrees(root)
    except (OSError, ValueError) as error:
        return f"creation state unknown for {location}: {error}"
    if target in registered:
        try:
            remove(str(target))
        except (OSError, ValueError) as error:
            return f"retained worktree {location}: {error}"
        return f"removed partial worktree {location}; branch was not deleted"
    if target.exists() or target.is_symlink():
        return f"retained unregistered path {location}; automatic removal refused"
    return f"no worktree remains at {location}; branch was not deleted"


def remove(raw: str) -> dict[str, str]:
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel")).resolve()
    parent = managed_parent(root)
    target = Path(raw)
    if not target.is_absolute() or ".." in target.parts or target.is_symlink():
        raise ValueError("removal requires an absolute, non-symlink managed worktree path")
    target = target.resolve()
    if target.parent != parent or not target.is_dir():
        raise ValueError(f"not a managed worktree below {parent}: {target}")
    registered = registered_worktrees(root)
    if target not in registered:
        raise ValueError(f"not a registered worktree: {target}")
    git(root, "worktree", "remove", "--", str(target))
    try:
        parent.rmdir()
    except OSError:
        pass
    return {"removed": str(target)}


def main(argv: list[str]) -> int:
    try:
        if len(argv) != 2 or argv[0] not in {"create", "remove"}:
            raise ValueError("usage: worktree.py create <branch> | remove <absolute-worktree-path>")
        result = create(argv[1]) if argv[0] == "create" else remove(argv[1])
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

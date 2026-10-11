#!/usr/bin/env python3
"""Create and remove managed worktrees without changing the caller's directory."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False,
    )
    if result.returncode:
        raise ValueError(os.fsdecode(result.stderr).strip())
    return os.fsdecode(result.stdout).strip()


def managed_parent(root: Path) -> Path:
    parent = root / ".codex" / "worktrees"
    if (root / ".codex").is_symlink() or parent.is_symlink():
        raise ValueError("managed worktree directories must not be symlinks")
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
        check=False,
    ).returncode == 0
    if existing:
        git(root, "worktree", "add", "--quiet", "--", str(target), branch)
    else:
        git(root, "worktree", "add", "--quiet", "-b", branch, "--", str(target), "HEAD")
    return {"main_root": str(root), "worktree_path": str(target), "branch": branch}


def remove(raw: str) -> dict[str, str]:
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel")).resolve()
    parent = managed_parent(root)
    target = Path(raw)
    if not target.is_absolute() or ".." in target.parts or target.is_symlink():
        raise ValueError("removal requires an absolute, non-symlink managed worktree path")
    target = target.resolve()
    if target.parent != parent or not target.is_dir():
        raise ValueError(f"not a managed worktree below {parent}: {target}")
    registered = {
        Path(item[9:]).resolve()
        for item in git(root, "worktree", "list", "--porcelain", "-z").split("\0")
        if item.startswith("worktree ")
    }
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

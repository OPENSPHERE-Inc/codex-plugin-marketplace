#!/usr/bin/env python3
"""Guard .codex/tmp descendants in this checkout or a registered sibling.

Plain mode checks lexical containment. -p also checks the physical parent;
-w checks the write target too. Exit 3 means a safely contained parent is
missing; callers may create it and recheck. Other violations exit 1.
"""

import os
import subprocess
import sys
from pathlib import Path

SCRATCH_ROOT = Path(".codex/tmp")


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


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    return 1


def to_windows_drive_path(raw):
    if os.name == "nt" and len(raw) >= 2 and raw[0] == "/" and raw[1].isalpha():
        if len(raw) == 2 or raw[2] == "/":
            return f"{raw[1].upper()}:{raw[2:]}"
    return raw


def git_path(root, argument):
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", argument],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, env=git_environment(),
    )
    if result.returncode != 0 or not result.stdout:
        return None
    return (root / os.fsdecode(result.stdout.removesuffix(b"\n"))).resolve()


def roots():
    yield Path.cwd()
    env_pwd = os.environ.get("PWD", "")
    if env_pwd:
        logical = Path(to_windows_drive_path(env_pwd))
        if logical.is_absolute() and logical.resolve() == Path.cwd():
            yield logical
    common_dir = git_path(Path.cwd(), "--git-common-dir")
    if common_dir is None:
        return
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain", "-z"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, env=git_environment(),
    )
    if result.returncode == 0:
        for field in result.stdout.split(b"\0"):
            if field.startswith(b"worktree "):
                root = Path(os.fsdecode(field[9:]))
                if (root.is_dir()
                        and git_path(root, "--show-toplevel") == root.resolve()
                        and git_path(root, "--git-common-dir") == common_dir):
                    yield root


def guard(mode, raw):
    target = Path(to_windows_drive_path(raw))
    if ".." in target.parts:
        return fail(f"path containing '..' is not allowed: {raw}")
    root = Path.cwd()
    if target.is_absolute():
        for candidate in roots():
            try:
                relative = target.relative_to(candidate / SCRATCH_ROOT)
            except ValueError:
                continue
            root = candidate
            break
        else:
            return fail(f"path is outside this repository's worktree scratch roots: {raw}")
    else:
        try:
            relative = target.relative_to(SCRATCH_ROOT)
        except ValueError:
            return fail(f"path is not under {SCRATCH_ROOT.as_posix()}/: {raw}")
    if not relative.parts:
        return fail(f"the bare {SCRATCH_ROOT.as_posix()}/ root is not allowed: {raw}")

    scratch = root / SCRATCH_ROOT
    full_target = scratch / relative
    if mode is not None:
        if scratch.is_symlink():
            return fail(f"scratch root is a symlink: {raw}")
        scratch_real = scratch.resolve()
        if not scratch_real.is_relative_to(root.resolve()):
            return fail(f"scratch root escapes its worktree: {raw}")
        ancestor = full_target.parent
        while not (ancestor.exists() or ancestor.is_symlink()):
            ancestor = ancestor.parent
        if ancestor.is_relative_to(scratch) and not ancestor.resolve().is_relative_to(scratch_real):
            return fail(f"resolved parent escapes scratch root: {raw}")
        if not ancestor.is_dir():
            return fail(f"parent is not a directory: {raw}")
        if mode == "-w" and not full_target.resolve().is_relative_to(scratch_real):
            return fail(f"resolved write target escapes scratch root: {raw}")
        if not full_target.parent.exists():
            return 3

    output = SCRATCH_ROOT / relative if root.resolve() == Path.cwd() else full_target
    sys.stdout.buffer.write((output.as_posix() + "\n").encode("utf-8"))
    return 0


def main(argv):
    mode = None
    args = list(argv)
    if args and args[0] in ("-p", "-w"):
        mode = args.pop(0)
    if len(args) != 1 or not args[0]:
        return fail("a path argument is required")
    try:
        return guard(mode, args[0])
    except (OSError, RuntimeError, ValueError) as error:
        return fail(str(error))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

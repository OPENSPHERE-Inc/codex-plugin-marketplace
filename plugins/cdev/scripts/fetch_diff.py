#!/usr/bin/env python3
"""Snapshot a worktree and capture only changes made after that snapshot."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
GUARD = SCRIPT_DIR / "lib" / "scratch_guard.py"
HASH_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
PATHSPEC = ["--", ":(top)", ":(top,exclude).codex/tmp", ":(exclude).codex/tmp"]
DIFF_PREFIX = [
    "git",
    "-c",
    "diff.noprefix=false",
    "-c",
    "diff.mnemonicPrefix=false",
    "diff",
    "--no-ext-diff",
    "--no-textconv",
    "--no-color",
]


class GitError(RuntimeError):
    pass


def run(command: list[str], *, env: dict[str, str] | None = None) -> bytes:
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(message or f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result.stdout


def text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def guard(raw: str, mode: str | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(GUARD)]
    if mode:
        command.append(mode)
    command.append(raw)
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def prepare_output(raw: str) -> Path:
    normalized = guard(raw)
    if normalized.returncode != 0:
        raise ValueError(normalized.stderr.strip())
    output = Path(normalized.stdout.strip())
    writable = guard(output.as_posix(), "-w")
    if writable.returncode == 3:
        output.parent.mkdir(parents=True, exist_ok=True)
        writable = guard(output.as_posix(), "-w")
    if writable.returncode != 0:
        raise ValueError(writable.stderr.strip())
    return output


def worktree_tree() -> str:
    with tempfile.TemporaryDirectory(prefix="cdev-index-") as temp_dir:
        temp_index = Path(temp_dir) / "index"
        real_index = Path(text(run(["git", "rev-parse", "--git-path", "index"])).strip())
        if real_index.is_file():
            shutil.copy2(real_index, temp_index)
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = str(temp_index)
        run(["git", "add", "-A"], env=env)
        return text(run(["git", "write-tree"], env=env)).strip()


def qa_diff(*args: str) -> str:
    return text(run([*DIFF_PREFIX, *args]))


def main(argv: list[str]) -> int:
    try:
        if argv[:1] == ["snapshot"] and len(argv) == 2:
            output = prepare_output(argv[1])
            output.write_text(worktree_tree() + "\n", encoding="utf-8")
            return 0

        if argv[:1] == ["diff"] and len(argv) == 3:
            baseline_file = Path(argv[1])
            output = prepare_output(argv[2])
            baseline = baseline_file.read_text(encoding="utf-8").strip()
            if not HASH_PATTERN.fullmatch(baseline):
                raise ValueError(f"baseline file does not contain a valid tree hash: {baseline_file}")
            current = worktree_tree()
            names = qa_diff("--name-status", baseline, current, *PATHSPEC)
            body = qa_diff(baseline, current, *PATHSPEC)
            output.write_text(
                "=== Changed Files (since coding start) ===\n"
                f"{names.rstrip()}\n\n"
                "=== Diff (since coding start) ===\n"
                f"{body.rstrip()}\n",
                encoding="utf-8",
            )
            return 0

        raise ValueError("usage: fetch_diff.py snapshot <tree-out-file> | diff <baseline-tree-file> <out-file>")
    except (GitError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

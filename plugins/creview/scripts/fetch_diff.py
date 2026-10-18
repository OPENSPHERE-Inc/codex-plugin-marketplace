#!/usr/bin/env python3
"""Capture a stable review diff without modifying the repository index."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from lib.scratch_guard import executable


SCRIPT_DIR = Path(__file__).resolve().parent
GUARD = SCRIPT_DIR / "lib" / "scratch_guard.py"
PATHSPEC = ["--", ":(top)", ":(top,exclude).codex/tmp", ":(top,exclude).codex/worktrees"]
DIFF_PREFIX = [
    "git",
    "-c",
    "diff.noprefix=false",
    "-c",
    "diff.mnemonicPrefix=false",
    "-c",
    "core.quotePath=false",
    "diff",
    "--no-ext-diff",
    "--no-textconv",
    "--no-color",
    "--submodule=short",
]


class GitError(RuntimeError):
    pass


def run(command: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> bytes:
    result = subprocess.run(
        [executable(command[0]), *command[1:]],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    if check and result.returncode != 0:
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


def review_diff(*args: str, env: dict[str, str] | None = None, attr_source=None) -> str:
    prefix = list(DIFF_PREFIX)
    if attr_source:
        prefix[1:1] = [f"--attr-source={attr_source}"]
        prefix.extend(["--no-renames", "--ignore-submodules=none"])
    # FIXME: text rendered as binary hides changed lines. Diff such text with --text.
    return text(run([*prefix, *args, *PATHSPEC], env=env))


def validate_revision(revision: str, env=None) -> None:
    command = ["git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{revision}^{{commit}}"]
    result = subprocess.run([executable(command[0]), *command[1:]], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if result.returncode != 0:
        raise ValueError(f"invalid revision: {revision}")


def untracked_diff() -> str:
    repo_root = Path(text(run(["git", "rev-parse", "--show-toplevel"])).strip())
    prefix = text(run(["git", "rev-parse", "--show-prefix"])).strip()
    listing = run(
        [
            "git",
            "-C",
            str(repo_root),
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            ":(exclude).codex/tmp",
            f":(exclude){prefix}.codex/tmp",
            ":(exclude).codex/worktrees",
            f":(exclude){prefix}.codex/worktrees",
        ]
    )
    paths = [os.fsdecode(item) for item in listing.split(b"\0") if item]
    if not paths:
        return ""

    with tempfile.TemporaryDirectory(prefix="creview-index-") as temp_dir:
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = str(Path(temp_dir) / "index")
        run(["git", "-C", str(repo_root), "add", "-N", "--", *paths], env=env)
        prefix = [DIFF_PREFIX[0], "-C", str(repo_root), *DIFF_PREFIX[1:]]
        names = text(run([*prefix, "--name-status"], env=env))
        body = text(run(prefix, env=env))
    return f"{names}\n{body}"


def parse_args(argv: list[str]) -> tuple[str, str, Path, bool, bool]:
    pr_mode = argv[:1] == ["--pr"]
    if argv[:1] in (["--range"], ["--pr"]):
        if len(argv) != 4:
            raise ValueError("usage: fetch_diff.py --range|--pr <from> <to> <output-file>")
        start, end, raw_output = argv[1], argv[2], argv[3]
        range_mode = True
    else:
        if len(argv) != 2:
            raise ValueError("usage: fetch_diff.py <base-branch> <output-file>")
        start, end, raw_output = argv[0], "HEAD", argv[1]
        range_mode = False
    return start, end, prepare_output(raw_output), range_mode, pr_mode


def main(argv: list[str]) -> int:
    try:
        start, end, output, range_mode, pr_mode = parse_args(argv)
        with tempfile.TemporaryDirectory(prefix="creview-hooks-") as no_hooks:
            env = None
            if pr_mode:
                from gh_pr import Error, hook_free_env
                try:
                    env = hook_free_env(no_hooks)
                except Error as error:
                    raise GitError(str(error)) from error
            validate_revision(start, env)
            validate_revision(end, env)
            merge_base = text(run(["git", "merge-base", start, end], env=env, check=False))
            diff_start = merge_base.strip() or start
            if pr_mode:
                try:
                    run(["git", f"--attr-source={diff_start}", "rev-parse", "--git-dir"], env=env)
                except GitError as error:
                    raise GitError(
                        "fetch_diff.py --pr requires Git 2.41 or later (--attr-source)"
                    ) from error
            options = {"env": env, "attr_source": diff_start if pr_mode else None}
            changed = review_diff("--name-status", f"{diff_start}..{end}", **options)
            log = text(run(["git", "log", f"{start}..{end}", "--oneline", "--no-color"], env=env))
            body = review_diff(f"{diff_start}..{end}", **options)
            sections = [
                f"=== Changed Files ({start}..{end}) ===\n{changed}",
                f"=== Commit Log ({start}..{end}) ===\n{log}",
                f"=== Commit Diff ({start}..{end}) ===\n{body}",
            ]
            if not range_mode:
                sections.extend([
                    f"=== Staged Changes ===\n{review_diff('--cached')}",
                    f"=== Unstaged Changes ===\n{review_diff()}",
                    f"=== Untracked Files ===\n{untracked_diff()}",
                ])
        output.write_text("\n".join(section.rstrip() + "\n" for section in sections), encoding="utf-8")
        return 0
    except (GitError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

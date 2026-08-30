#!/usr/bin/env python3
"""Capture a stable review diff without modifying the repository index."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
GUARD = SCRIPT_DIR / "lib" / "scratch_guard.py"
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


def run(command: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> bytes:
    result = subprocess.run(
        command,
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


def review_diff(*args: str, env: dict[str, str] | None = None) -> str:
    return text(run([*DIFF_PREFIX, *args], env=env))


def validate_revision(revision: str) -> None:
    command = ["git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{revision}^{{commit}}"]
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
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
        ]
    )
    paths = [os.fsdecode(item) for item in listing.split(b"\0") if item]
    if not paths:
        return ""

    with tempfile.TemporaryDirectory(prefix="creview-index-") as temp_dir:
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = str(Path(temp_dir) / "index")
        run(["git", "-C", str(repo_root), "add", "-N", "--", *paths], env=env)
        names = text(
            run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "-c",
                    "diff.noprefix=false",
                    "-c",
                    "diff.mnemonicPrefix=false",
                    "diff",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--no-color",
                    "--name-status",
                ],
                env=env,
            )
        )
        body = text(
            run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "-c",
                    "diff.noprefix=false",
                    "-c",
                    "diff.mnemonicPrefix=false",
                    "diff",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--no-color",
                ],
                env=env,
            )
        )
    return f"{names}\n{body}"


def parse_args(argv: list[str]) -> tuple[str, str, Path, bool]:
    if argv[:1] == ["--range"]:
        if len(argv) != 4:
            raise ValueError("usage: fetch_diff.py --range <from> <to> <output-file>")
        start, end, raw_output = argv[1], argv[2], argv[3]
        range_mode = True
    else:
        if len(argv) != 2:
            raise ValueError("usage: fetch_diff.py <base-branch> <output-file>")
        start, end, raw_output = argv[0], "HEAD", argv[1]
        range_mode = False
    return start, end, prepare_output(raw_output), range_mode


def main(argv: list[str]) -> int:
    try:
        start, end, output, range_mode = parse_args(argv)
        validate_revision(start)
        validate_revision(end)

        merge_base = subprocess.run(
            ["git", "merge-base", start, end],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        diff_start = text(merge_base.stdout).strip() if merge_base.returncode == 0 else start

        sections = [
            f"=== Changed Files ({start}..{end}) ===\n{review_diff('--name-status', f'{diff_start}..{end}')}",
            f"=== Commit Log ({start}..{end}) ===\n{text(run(['git', 'log', f'{start}..{end}', '--oneline', '--no-color']))}",
            f"=== Commit Diff ({start}..{end}) ===\n{review_diff(f'{diff_start}..{end}')}",
        ]
        if not range_mode:
            sections.extend(
                [
                    f"=== Staged Changes ===\n{review_diff('--cached')}",
                    f"=== Unstaged Changes ===\n{review_diff()}",
                    f"=== Untracked Files ===\n{untracked_diff()}",
                ]
            )
        output.write_text("\n".join(section.rstrip() + "\n" for section in sections), encoding="utf-8")
        return 0
    except (GitError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

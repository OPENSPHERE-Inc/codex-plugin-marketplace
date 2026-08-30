#!/usr/bin/env python3
"""Delete selected paths below the current project's .codex/tmp directory."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
GUARD = SCRIPT_DIR / "lib" / "scratch_guard.py"


def guarded_path(raw: str) -> tuple[int, Path | None]:
    result = subprocess.run(
        [sys.executable, str(GUARD), "-p", raw],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 3:
        return 3, None
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode, None
    return 0, Path(result.stdout.strip())


def remove_target(target: Path) -> None:
    if target.is_symlink() or target.is_file():
        target.unlink(missing_ok=True)
    elif target.is_dir():
        shutil.rmtree(target)


def main(argv: list[str]) -> int:
    if not argv:
        print("Error: at least one path is required", file=sys.stderr)
        return 2

    for raw in argv:
        status, target = guarded_path(raw)
        if status == 3:
            continue
        if status != 0 or target is None:
            return 1
        remove_target(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CDEV_SCRIPTS = ROOT / "plugins" / "cdev" / "scripts"
CREVIEW_SCRIPTS = ROOT / "plugins" / "creview" / "scripts"


def run(
    command: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=repo)


def init_repo(repo: Path) -> None:
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Codex Plugin Test")
    git(repo, "config", "user.email", "codex-plugin-test@example.invalid")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-q", "-m", "base")


class ScratchGuardTests(unittest.TestCase):
    def test_accepts_only_descendants_of_scratch_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-plugin-guard-") as temp:
            repo = Path(temp)
            target = repo / ".codex" / "tmp" / "run" / "result.jsonl"
            target.parent.mkdir(parents=True)
            script = CDEV_SCRIPTS / "lib" / "scratch_guard.py"

            accepted = run(
                [sys.executable, str(script), target.as_posix()],
                cwd=repo,
            )
            self.assertEqual(
                accepted.stdout.strip(),
                ".codex/tmp/run/result.jsonl",
            )

            for raw in (".codex/tmp", "../outside", "outside/result.jsonl"):
                rejected = run(
                    [sys.executable, str(script), raw],
                    cwd=repo,
                    check=False,
                )
                self.assertNotEqual(rejected.returncode, 0, raw)

    def test_delete_helper_cannot_escape_scratch_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-plugin-delete-") as temp:
            repo = Path(temp)
            target = repo / ".codex" / "tmp" / "run"
            target.mkdir(parents=True)
            (target / "artifact.txt").write_text("temporary\n", encoding="utf-8")
            outside = repo / "outside.txt"
            outside.write_text("keep\n", encoding="utf-8")
            script = CDEV_SCRIPTS / "del_tmp.py"

            run([sys.executable, str(script), ".codex/tmp/run"], cwd=repo)
            self.assertFalse(target.exists())
            self.assertTrue(outside.exists())

            rejected = run(
                [sys.executable, str(script), "outside.txt"],
                cwd=repo,
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertTrue(outside.exists())


class DiffHelperTests(unittest.TestCase):
    def test_cdev_snapshot_diff_includes_only_post_snapshot_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-plugin-cdev-") as temp:
            repo = Path(temp)
            init_repo(repo)
            script = CDEV_SCRIPTS / "fetch_diff.py"
            baseline = ".codex/tmp/cdev/baseline.txt"
            output = ".codex/tmp/cdev/coding.diff"

            run(
                [sys.executable, str(script), "snapshot", baseline],
                cwd=repo,
            )
            (repo / "tracked.txt").write_text("base\nchanged\n", encoding="utf-8")
            (repo / "new.txt").write_text("new\n", encoding="utf-8")
            run(
                [sys.executable, str(script), "diff", baseline, output],
                cwd=repo,
            )

            diff = (repo / output).read_text(encoding="utf-8")
            self.assertIn("tracked.txt", diff)
            self.assertIn("new.txt", diff)
            self.assertIn("+changed", diff)
            self.assertEqual(git(repo, "diff", "--cached", "--name-only").stdout, "")

    def test_creview_diff_captures_committed_and_worktree_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-plugin-creview-") as temp:
            repo = Path(temp)
            init_repo(repo)
            (repo / "tracked.txt").write_text("base\nfeature\n", encoding="utf-8")
            git(repo, "add", "tracked.txt")
            git(repo, "commit", "-q", "-m", "feature")

            (repo / "staged.txt").write_text("staged\n", encoding="utf-8")
            git(repo, "add", "staged.txt")
            (repo / "tracked.txt").write_text(
                "base\nfeature\nunstaged\n",
                encoding="utf-8",
            )
            (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")

            script = CREVIEW_SCRIPTS / "fetch_diff.py"
            output = ".codex/tmp/creview/review.diff"
            run(
                [sys.executable, str(script), "HEAD~1", output],
                cwd=repo,
            )

            diff = (repo / output).read_text(encoding="utf-8")
            self.assertIn("=== Commit Diff (HEAD~1..HEAD) ===", diff)
            self.assertIn("+feature", diff)
            self.assertIn("=== Staged Changes ===", diff)
            self.assertIn("staged.txt", diff)
            self.assertIn("=== Unstaged Changes ===", diff)
            self.assertIn("+unstaged", diff)
            self.assertIn("=== Untracked Files ===", diff)
            self.assertIn("untracked.txt", diff)


if __name__ == "__main__":
    unittest.main()

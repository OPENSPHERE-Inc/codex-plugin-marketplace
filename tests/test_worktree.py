from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_helpers import CDEV_SCRIPTS, CREVIEW_SCRIPTS, ROOT, git, init_repo, run


WORKTREE = ROOT / "plugins/cprompt/scripts/worktree.py"


class WorktreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="codex worktree ")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "main repo"
        self.repo.mkdir()
        init_repo(self.repo)

    def helper(self, *args: str, cwd: Path | None = None, check: bool = True):
        return run([sys.executable, str(WORKTREE), *args], cwd=cwd or self.repo, check=check)

    def create(self, branch: str = "task/new") -> Path:
        result = json.loads(self.helper("create", branch).stdout)
        self.assertEqual(Path(result["main_root"]).resolve(), self.repo.resolve())
        self.assertEqual(result["branch"], branch)
        return Path(result["worktree_path"])

    def symlink(self, target: Path, link: Path, directory: bool = False) -> None:
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")

    def test_new_branch_preserves_dirty_main_index_and_worktree(self) -> None:
        (self.repo / "tracked.txt").write_text("staged\n")
        git(self.repo, "add", "tracked.txt")
        (self.repo / "tracked.txt").write_text("unstaged\n")
        (self.repo / "user.txt").write_text("untracked\n")
        staged = git(self.repo, "diff", "--cached").stdout
        target = self.create()
        self.assertEqual((target / "tracked.txt").read_text(), "base\n")
        self.assertFalse((target / "user.txt").exists())
        self.assertEqual(git(self.repo, "diff", "--cached").stdout, staged)
        (target / "tracked.txt").write_text("feature\n")
        git(target, "add", "tracked.txt")
        git(target, "commit", "-q", "-m", "feature")
        head = git(target, "rev-parse", "HEAD").stdout
        self.helper("remove", str(target))
        self.assertFalse(target.exists())
        self.assertFalse(target.parent.exists())
        self.assertEqual(git(self.repo, "rev-parse", "task/new").stdout, head)
        self.assertEqual((self.repo / "tracked.txt").read_text(), "unstaged\n")
        self.assertEqual(git(self.repo, "diff", "--cached").stdout, staged)

    def test_existing_branch_starts_at_its_tip(self) -> None:
        original = git(self.repo, "branch", "--show-current").stdout.strip()
        git(self.repo, "switch", "-q", "-c", "existing")
        (self.repo / "tracked.txt").write_text("existing tip\n")
        git(self.repo, "commit", "-qam", "existing tip")
        git(self.repo, "switch", "-q", original)
        target = self.create("existing")
        self.assertEqual((target / "tracked.txt").read_text(), "existing tip\n")

    def test_checked_out_branch_invalid_names_and_path_collisions_fail(self) -> None:
        current = git(self.repo, "branch", "--show-current").stdout.strip()
        for branch in (current, "", "-bad", "../escape", "with space", "@{-1}"):
            with self.subTest(branch=branch):
                self.assertNotEqual(self.helper("create", branch, check=False).returncode, 0)
        self.create("topic/one")
        self.assertNotEqual(self.helper("create", "topic-one", check=False).returncode, 0)
        self.assertNotEqual(self.helper("create", "topic/one", check=False).returncode, 0)

    def test_subdirectory_start_rejected(self) -> None:
        subdir = self.repo / "subdir"
        subdir.mkdir()
        self.assertNotEqual(self.helper("create", "task", cwd=subdir, check=False).returncode, 0)
        self.assertFalse((self.repo / ".codex/worktrees").exists())

    def test_dirty_and_locked_worktrees_are_retained(self) -> None:
        target = self.create()
        (target / "tracked.txt").write_text("keep\n")
        self.assertNotEqual(self.helper("remove", str(target), check=False).returncode, 0)
        git(target, "add", "tracked.txt")
        self.assertNotEqual(self.helper("remove", str(target), check=False).returncode, 0)
        git(target, "commit", "-qm", "keep")
        untracked = target / "new.txt"
        untracked.write_text("keep too\n")
        self.assertNotEqual(self.helper("remove", str(target), check=False).returncode, 0)
        untracked.unlink()
        git(self.repo, "worktree", "lock", str(target))
        self.assertNotEqual(self.helper("remove", str(target), check=False).returncode, 0)
        self.assertTrue(target.exists())

    def test_removal_rejects_unmanaged_or_unregistered_paths(self) -> None:
        external = self.repo.parent / "external"
        git(self.repo, "worktree", "add", "-q", "-b", "external", str(external))
        fake = self.repo / ".codex/worktrees/fake"
        fake.mkdir(parents=True)
        for target in (self.repo, external, fake, Path(".codex/worktrees/fake")):
            with self.subTest(target=target):
                self.assertNotEqual(self.helper("remove", str(target), check=False).returncode, 0)
        self.assertTrue(external.exists())
        self.assertTrue(fake.exists())

    def test_managed_directory_symlink_is_rejected(self) -> None:
        outside = self.repo.parent / "outside"
        outside.mkdir()
        self.symlink(outside, self.repo / ".codex", True)
        self.assertNotEqual(self.helper("create", "task", check=False).returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_ignored_files_are_removed_with_clean_worktree(self) -> None:
        (self.repo / ".gitignore").write_text("ignored/\n")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-qm", "ignore build output")
        target = self.create()
        (target / "ignored").mkdir()
        (target / "ignored/build.log").write_text("disposable")
        self.helper("remove", str(target))
        self.assertFalse(target.exists())

    def test_cross_worktree_diff_output_and_cleanup(self) -> None:
        target = self.create()
        scratch = self.repo / ".codex/tmp/run"
        for plugin, script in (("cdev", CDEV_SCRIPTS), ("creview", CREVIEW_SCRIPTS)):
            with self.subTest(plugin=plugin):
                output = scratch / (plugin + ".diff")
                if plugin == "cdev":
                    baseline = scratch / "baseline"
                    run([sys.executable, str(script / "fetch_diff.py"), "snapshot", str(baseline)], cwd=target)
                    (target / "tracked.txt").write_text("change one\n")
                    args = ["diff", str(baseline), str(output)]
                else:
                    args = ["HEAD", str(output)]
                run([sys.executable, str(script / "fetch_diff.py"), *args], cwd=target)
                self.assertIn("tracked.txt", output.read_text())
                self.assertIn("+change one", output.read_text())
        run([sys.executable, str(CDEV_SCRIPTS / "del_tmp.py"), str(scratch)], cwd=target)
        self.assertFalse(scratch.exists())
        self.assertEqual((self.repo / "tracked.txt").read_text(), "base\n")

    def test_guard_accepts_siblings_but_rejects_foreign_repositories_and_traversal(self) -> None:
        target = self.create()
        foreign = self.repo.parent / "foreign"
        foreign.mkdir()
        init_repo(foreign)
        guard = CDEV_SCRIPTS / "lib/scratch_guard.py"
        accepted = self.repo / ".codex/tmp/run/result"
        missing = run([sys.executable, str(guard), "-w", str(accepted)], cwd=target, check=False)
        self.assertEqual(missing.returncode, 3)
        accepted.parent.mkdir(parents=True)
        for mode in ("-p", "-w"):
            result = run([sys.executable, str(guard), mode, str(accepted)], cwd=target)
            self.assertEqual(Path(result.stdout.strip()), accepted)
        for raw in (str(foreign / ".codex/tmp/run"), str(self.repo / ".codex/tmp"),
                    str(self.repo / ".codex/tmp/../outside"), str(self.repo / "tracked.txt")):
            with self.subTest(raw=raw):
                self.assertNotEqual(run([sys.executable, str(guard), "-w", raw], cwd=target, check=False).returncode, 0)

    def test_guard_rejects_symlink_escapes_and_delete_only_unlinks_leaf(self) -> None:
        target = self.create()
        scratch = self.repo / ".codex/tmp"
        scratch.mkdir(parents=True)
        outside = self.repo.parent / "outside"
        outside.mkdir()
        sentinel = outside / "keep"
        sentinel.write_text("keep")
        link = scratch / "escape"
        self.symlink(outside, link, True)
        guard = CDEV_SCRIPTS / "lib/scratch_guard.py"
        for raw in (link / "keep", link / "missing/nested/result", link):
            result = run([sys.executable, str(guard), "-w", str(raw)], cwd=target, check=False)
            self.assertEqual(result.returncode, 1)
        run([sys.executable, str(CDEV_SCRIPTS / "del_tmp.py"), str(link)], cwd=target)
        self.assertFalse(link.exists())
        self.assertEqual(sentinel.read_text(), "keep")

    def test_guard_rejects_symlinked_scratch_root(self) -> None:
        target = self.create()
        outside = self.repo.parent / "outside"
        outside.mkdir()
        self.symlink(outside, self.repo / ".codex/tmp", True)
        guard = CDEV_SCRIPTS / "lib/scratch_guard.py"
        result = run([sys.executable, str(guard), "-w", str(self.repo / ".codex/tmp/run")],
                     cwd=target, check=False)
        self.assertEqual(result.returncode, 1)

    def test_unrelated_pwd_environment_does_not_authorize_another_directory(self) -> None:
        target = self.create()
        foreign = self.repo.parent / "foreign"
        foreign.mkdir()
        result = subprocess.run(
            [sys.executable, str(CDEV_SCRIPTS / "lib/scratch_guard.py"),
             str(foreign / ".codex/tmp/run")],
            cwd=target, env={**os.environ, "PWD": str(foreign)}, capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_diff_helpers_exclude_worktrees_and_scratch_even_when_tracked(self) -> None:
        for name in (".codex/tmp/record", ".codex/worktrees/record"):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("base artifact\n")
            git(self.repo, "add", name)
        git(self.repo, "commit", "-qm", "tracked artifacts")
        baseline = ".codex/tmp/baseline"
        run([sys.executable, str(CDEV_SCRIPTS / "fetch_diff.py"), "snapshot", baseline], cwd=self.repo)
        for name in (".codex/tmp/record", ".codex/worktrees/record"):
            (self.repo / name).write_text("excluded artifact\n")
        self.create()
        (self.repo / "tracked.txt").write_text("source change\n")
        for script, args in ((CDEV_SCRIPTS, ["diff", baseline]), (CREVIEW_SCRIPTS, ["HEAD~1"])):
            output = ".codex/tmp/" + script.parent.name + ".diff"
            run([sys.executable, str(script / "fetch_diff.py"), *args, output], cwd=self.repo)
            text = (self.repo / output).read_text()
            self.assertIn("+source change", text)
            self.assertNotIn("excluded artifact", text)
            self.assertNotIn("base artifact", text)
            self.assertNotIn("task-new", text)
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only").stdout, "")


class SharedHelperTests(unittest.TestCase):
    def test_worktree_and_guard_copies_match(self) -> None:
        for relative, plugins in (
            ("scripts/worktree.py", ("cprompt", "creview", "cdev")),
            ("scripts/lib/scratch_guard.py", ("creview", "cdev")),
        ):
            with self.subTest(helper=relative):
                copies = [(ROOT / tree / plugin / relative).read_bytes()
                          for tree in ("src", "plugins") for plugin in plugins]
                self.assertTrue(all(content == copies[0] for content in copies))


if __name__ == "__main__":
    unittest.main()

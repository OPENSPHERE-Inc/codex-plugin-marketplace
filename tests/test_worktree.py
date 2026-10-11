from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from test_helpers import CDEV_SCRIPTS, CREVIEW_SCRIPTS, ROOT, git, init_repo, run


WORKTREE = ROOT / "plugins/cprompt/scripts/worktree.py"


class WorktreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="codex worktree ")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve() / "main repo"
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

    def test_inherited_index_does_not_change_the_main_index(self) -> None:
        (self.repo / "tracked.txt").write_text("staged\n")
        git(self.repo, "add", "tracked.txt")
        staged = git(self.repo, "diff", "--cached").stdout
        index = self.repo / ".git/index"
        index_bytes = index.read_bytes()
        with patch.dict(os.environ, {"GIT_INDEX_FILE": str(index)}):
            target = self.create()
            self.helper("remove", str(target))
        self.assertEqual(index.read_bytes(), index_bytes)
        self.assertEqual(git(self.repo, "diff", "--cached").stdout, staged)
        self.assertEqual((self.repo / "tracked.txt").read_text(), "staged\n")

    def test_inherited_repository_environment_cannot_redirect_worktree_operations(self) -> None:
        foreign = self.repo.parent / "foreign"
        foreign.mkdir()
        init_repo(foreign)
        (foreign / "tracked.txt").write_text("foreign\n")
        git(foreign, "commit", "-qam", "foreign")
        before = git(foreign, "worktree", "list", "--porcelain").stdout
        environments = (
            {"GIT_DIR": str(foreign / ".git")},
            {"GIT_DIR": str(foreign / ".git"), "GIT_WORK_TREE": str(foreign),
             "GIT_COMMON_DIR": str(foreign / ".git")},
            {"GIT_COMMON_DIR": str(foreign / ".git")},
            {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.worktree",
             "GIT_CONFIG_VALUE_0": str(foreign)},
        )
        for number, environment in enumerate(environments):
            with self.subTest(environment=environment):
                with patch.dict(os.environ, environment):
                    target = self.create(f"isolated-{number}")
                    self.assertEqual((target / "tracked.txt").read_text(), "base\n")
                    self.helper("remove", str(target))
                self.assertFalse(target.exists())
                self.assertEqual(git(foreign, "worktree", "list", "--porcelain").stdout, before)
                foreign_branch = run(
                    ["git", "show-ref", "--verify", "--quiet", f"refs/heads/isolated-{number}"],
                    cwd=foreign, check=False,
                )
                self.assertNotEqual(foreign_branch.returncode, 0)
                self.assertEqual((foreign / "tracked.txt").read_text(), "foreign\n")

    def test_checked_out_branch_invalid_names_and_path_collisions_fail(self) -> None:
        current = git(self.repo, "branch", "--show-current").stdout.strip()
        for branch in (current, "", "-bad", "../escape", "with space", "@{-1}"):
            with self.subTest(branch=branch):
                self.assertNotEqual(self.helper("create", branch, check=False).returncode, 0)
        self.create("topic/one")
        self.assertNotEqual(self.helper("create", "topic-one", check=False).returncode, 0)
        self.assertNotEqual(self.helper("create", "topic/one", check=False).returncode, 0)

    def checkout_hook(self, body: str) -> Path:
        hook = self.repo / ".git/hooks/post-checkout"
        hook.write_text("#!/bin/sh\n" + body, encoding="utf-8", newline="\n")
        hook.chmod(0o755)
        return hook

    def test_competing_creates_preserve_the_successful_worktree(self) -> None:
        (self.repo / ".gitignore").write_text("ignored/\n")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-qm", "ignore build output")
        for first_branch, second_branch in (("same", "same"), ("topic/one", "topic-one")):
            with self.subTest(branches=(first_branch, second_branch)):
                module = runpy.run_path(str(WORKTREE))
                create = module["create"]
                real_git = create.__globals__["git"]
                before_add = threading.Event()
                second_finished = threading.Event()
                caller = threading.local()

                def controlled_git(root, *args):
                    if args[:2] == ("worktree", "add") and caller.first:
                        before_add.set()
                        if not second_finished.wait(10):
                            raise AssertionError("second create did not finish")
                    return real_git(root, *args)

                def attempt(branch, first):
                    caller.first = first
                    try:
                        result = create(branch)
                        target = Path(result["worktree_path"])
                        (target / "ignored").mkdir()
                        (target / "ignored/keep").write_text("keep\n")
                        return result
                    except (OSError, ValueError) as error:
                        return error
                    finally:
                        if not first:
                            second_finished.set()

                with patch.object(Path, "cwd", return_value=self.repo), patch.dict(
                    create.__globals__, {"git": controlled_git},
                ), ThreadPoolExecutor(max_workers=2) as executor:
                    first = executor.submit(attempt, first_branch, True)
                    self.assertTrue(before_add.wait(10), "first create did not reach Git add")
                    second = executor.submit(attempt, second_branch, False)
                    results = [first.result(timeout=15), second.result(timeout=15)]
                successes = [result for result in results if isinstance(result, dict)]
                self.assertEqual(len(successes), 1, results)
                target = Path(successes[0]["worktree_path"])
                self.assertTrue(target.is_dir(), results)
                self.assertEqual((target / "tracked.txt").read_text(), "base\n")
                self.assertEqual((target / "ignored/keep").read_text(), "keep\n")
                self.assertIn(target, module["registered_worktrees"](self.repo))
                self.helper("remove", str(target))

    def test_failed_reservation_never_adds_or_cleans_another_path(self) -> None:
        module = runpy.run_path(str(WORKTREE))
        create = module["create"]
        target = self.repo / ".codex/worktrees/reserved"
        real_mkdir = Path.mkdir

        def competing_mkdir(path, *args, **kwargs):
            if path == target:
                real_mkdir(path)
                (path / "keep").write_text("keep\n")
            return real_mkdir(path, *args, **kwargs)

        with patch.object(Path, "cwd", return_value=self.repo), patch.object(
            Path, "mkdir", competing_mkdir,
        ), patch.dict(create.__globals__):
            cleanup = Mock()
            observed_git = Mock(wraps=create.__globals__["git"])
            create.__globals__.update(git=observed_git, cleanup_failed_create=cleanup)
            with self.assertRaises((OSError, ValueError)):
                create("reserved")
            cleanup.assert_not_called()
            self.assertFalse(any(call.args[1:3] == ("worktree", "add")
                                 for call in observed_git.call_args_list))
        self.assertEqual((target / "keep").read_text(), "keep\n")

    def test_stale_registration_is_rejected_before_add_or_cleanup(self) -> None:
        target = self.create("stale")
        moved = self.repo.parent / "moved-worktree"
        target.rename(moved)
        module = runpy.run_path(str(WORKTREE))
        create = module["create"]
        cleanup = Mock()
        observed_git = Mock(wraps=create.__globals__["git"])
        with patch.object(Path, "cwd", return_value=self.repo), patch.dict(
            create.__globals__, {"git": observed_git, "cleanup_failed_create": cleanup},
        ):
            with self.assertRaises((OSError, ValueError)):
                create("stale")
        cleanup.assert_not_called()
        self.assertFalse(any(call.args[1:3] == ("worktree", "add")
                             for call in observed_git.call_args_list))
        self.assertIn(target, module["registered_worktrees"](self.repo))
        self.assertEqual((moved / "tracked.txt").read_text(), "base\n")

    def test_cleanup_without_reservation_preserves_existing_registration(self) -> None:
        target = self.create("existing")
        module = runpy.run_path(str(WORKTREE))
        with patch.object(Path, "cwd", return_value=self.repo):
            result = module["cleanup_failed_create"](self.repo, target, "existing")
        self.assertIn("retained", result)
        self.assertIn(str(target), result)
        self.assertIn(target, module["registered_worktrees"](self.repo))
        self.assertEqual((target / "tracked.txt").read_text(), "base\n")

    def test_failed_create_preserves_replaced_reservation(self) -> None:
        for registered in (False, True):
            with self.subTest(registered=registered):
                branch = f"replacement-{registered}"
                target = self.repo / ".codex/worktrees" / branch
                moved = self.repo.parent / f"reserved-{registered}"
                module = runpy.run_path(str(WORKTREE))
                create = module["create"]
                real_git = create.__globals__["git"]

                def replace_reservation(root, *args):
                    if args[:2] == ("worktree", "add"):
                        target.rename(moved)
                        if registered:
                            real_git(root, *args)
                        else:
                            target.mkdir()
                        raise ValueError("injected failure after target replacement")
                    return real_git(root, *args)

                with patch.object(Path, "cwd", return_value=self.repo), patch.dict(
                    create.__globals__, {"git": replace_reservation},
                ):
                    with self.assertRaisesRegex(ValueError, "ownership") as raised:
                        create(branch)
                self.assertIn(str(target), str(raised.exception))
                self.assertTrue(target.is_dir())
                if registered:
                    self.assertIn(target, module["registered_worktrees"](self.repo))
                    self.assertEqual((target / "tracked.txt").read_text(), "base\n")
                self.assertTrue(moved.is_dir())

    def test_failure_before_add_releases_only_an_empty_owned_reservation(self) -> None:
        for dirty in (False, True):
            with self.subTest(dirty=dirty):
                branch = f"before-add-{dirty}"
                target = self.repo / ".codex/worktrees" / branch
                module = runpy.run_path(str(WORKTREE))
                create = module["create"]
                real_run = subprocess.run

                def fail_show_ref(command, **kwargs):
                    if command[3:4] == ["show-ref"]:
                        if dirty:
                            (target / "keep").write_text("keep\n")
                        raise OSError("injected failure before Git add")
                    return real_run(command, **kwargs)

                with patch.object(Path, "cwd", return_value=self.repo), patch.object(
                    subprocess, "run", side_effect=fail_show_ref,
                ):
                    with self.assertRaisesRegex(ValueError, "injected failure") as raised:
                        create(branch)
                self.assertIn(str(target), str(raised.exception))
                self.assertNotIn(target, module["registered_worktrees"](self.repo))
                self.assertEqual(target.exists(), dirty)
                if dirty:
                    self.assertEqual((target / "keep").read_text(), "keep\n")

    def test_failed_checkout_hook_cleans_worktree_and_allows_retry(self) -> None:
        hook = self.checkout_hook("exit 1\n")
        (self.repo / "tracked.txt").write_text("staged\n")
        git(self.repo, "add", "tracked.txt")
        staged = git(self.repo, "diff", "--cached").stdout
        target = self.repo / ".codex/worktrees/hook-failure"
        failed = self.helper("create", "hook-failure", check=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("git worktree add", failed.stderr)
        self.assertIn("exit 1", failed.stderr)
        self.assertFalse(target.exists())
        registered = {
            Path(field[9:]).resolve()
            for field in git(self.repo, "worktree", "list", "--porcelain", "-z").stdout.split("\0")
            if field.startswith("worktree ")
        }
        self.assertNotIn(target.resolve(), registered)
        git(self.repo, "show-ref", "--verify", "refs/heads/hook-failure")
        self.assertEqual(git(self.repo, "diff", "--cached").stdout, staged)
        hook.unlink()
        recreated = self.create("hook-failure")
        self.helper("remove", str(recreated))

    def test_failed_checkout_hook_retains_dirty_or_locked_worktree(self) -> None:
        for branch, body in (
            ("dirty-hook", "printf 'keep\\n' > hook-data.txt\nexit 1\n"),
            ("locked-hook", "git worktree lock .\nexit 1\n"),
        ):
            with self.subTest(branch=branch):
                self.checkout_hook(body)
                target = self.repo / ".codex/worktrees" / branch
                failed = self.helper("create", branch, check=False)
                self.assertNotEqual(failed.returncode, 0)
                self.assertIn(str(target), failed.stderr)
                self.assertIn(branch, failed.stderr)
                self.assertIn("retained", failed.stderr)
                self.assertTrue(target.is_dir())
                listing = git(self.repo, "worktree", "list", "--porcelain", "-z").stdout
                registered = {
                    Path(field[9:]).resolve() for field in listing.split("\0")
                    if field.startswith("worktree ")
                }
                self.assertIn(target.resolve(), registered)
                git(self.repo, "show-ref", "--verify", f"refs/heads/{branch}")
                if branch == "dirty-hook":
                    self.assertEqual((target / "hook-data.txt").read_text(), "keep\n")
                else:
                    self.assertIn("locked", listing)

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

    def test_managed_parent_rejects_resolved_directory_redirects(self) -> None:
        managed_parent = runpy.run_path(str(WORKTREE))["managed_parent"]
        for relative in (".codex", ".codex/worktrees"):
            for inside in (False, True):
                with self.subTest(relative=relative, inside=inside):
                    redirected = (self.repo if inside else self.repo.parent) / "redirected"
                    redirected.mkdir(exist_ok=True)
                    link = self.repo / relative
                    link.parent.mkdir(exist_ok=True)
                    self.symlink(redirected, link, True)
                    try:
                        with patch.object(Path, "is_symlink", return_value=False):
                            with self.assertRaisesRegex(ValueError, "resolve"):
                                managed_parent(self.repo)
                    finally:
                        link.unlink()

    @unittest.skipUnless(os.name == "nt", "directory junctions require Windows")
    def test_managed_directory_junctions_preserve_targets_and_registration(self) -> None:
        for relative in (".codex", ".codex/worktrees"):
            for inside in (False, True):
                with self.subTest(relative=relative, inside=inside):
                    name = f"redirect-{relative.count('/')}-{inside}"
                    redirected = (self.repo if inside else self.repo.parent) / name
                    redirected.mkdir()
                    physical_parent = (
                        redirected / "worktrees" if relative == ".codex" else redirected
                    )
                    target = physical_parent / "existing"
                    git(self.repo, "worktree", "add", "-q", "-b", name, str(target))
                    link = self.repo / relative
                    link.parent.mkdir(exist_ok=True)
                    junction = run(
                        ["cmd", "/c", "mklink", "/J", str(link), str(redirected)],
                        cwd=self.repo, check=False,
                    )
                    if junction.returncode:
                        self.skipTest(f"directory junctions unavailable: {junction.stderr}")
                    try:
                        before = git(self.repo, "worktree", "list", "--porcelain", "-z").stdout
                        contents = {path.relative_to(redirected): path.read_bytes()
                                    for path in redirected.rglob("*") if path.is_file()}
                        created = self.helper("create", f"new-{name}", check=False)
                        self.assertNotEqual(created.returncode, 0)
                        alias = self.repo / ".codex/worktrees/existing"
                        for raw in (alias, target):
                            removed = self.helper("remove", str(raw), check=False)
                            self.assertNotEqual(removed.returncode, 0)
                        self.assertEqual(
                            git(self.repo, "worktree", "list", "--porcelain", "-z").stdout, before,
                        )
                        self.assertEqual(
                            {path.relative_to(redirected): path.read_bytes()
                             for path in redirected.rglob("*") if path.is_file()}, contents,
                        )
                        branch = run(
                            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/new-{name}"],
                            cwd=self.repo, check=False,
                        )
                        self.assertNotEqual(branch.returncode, 0)
                    finally:
                        link.rmdir()

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

    def test_guard_rejects_reused_stale_worktree_registrations(self) -> None:
        for reuse in ("foreign-repository", "ordinary-subdirectory"):
            with self.subTest(reuse=reuse):
                stale = self.create(reuse)
                stale.rename(self.repo.parent / f"moved-{reuse}")
                stale.mkdir()
                if reuse == "foreign-repository":
                    init_repo(stale)
                listing = git(self.repo, "worktree", "list", "--porcelain", "-z").stdout
                registered = {
                    Path(field[9:]).resolve() for field in listing.split("\0")
                    if field.startswith("worktree ")
                }
                self.assertIn(stale, registered)
                scratch = stale / ".codex/tmp/run"
                scratch.mkdir(parents=True)
                sentinel = scratch / "keep"
                sentinel.write_text("keep")
                for scripts in (CDEV_SCRIPTS, CREVIEW_SCRIPTS):
                    guard = scripts / "lib/scratch_guard.py"
                    for mode in ([], ["-p"], ["-w"]):
                        rejected = run(
                            [sys.executable, str(guard), *mode, str(sentinel)],
                            cwd=self.repo, check=False,
                        )
                        self.assertEqual(rejected.returncode, 1)
                    deletion = run(
                        [sys.executable, str(scripts / "del_tmp.py"), str(scratch)],
                        cwd=self.repo, check=False,
                    )
                    self.assertEqual(deletion.returncode, 1)
                    self.assertEqual(sentinel.read_text(), "keep")

    def test_inherited_repository_environment_cannot_authorize_foreign_scratch(self) -> None:
        target = self.create()
        foreign = self.repo.parent / "foreign"
        foreign.mkdir()
        init_repo(foreign)
        scratch = foreign / ".codex/tmp/run"
        guard = CDEV_SCRIPTS / "lib/scratch_guard.py"
        cleanup = CREVIEW_SCRIPTS / "del_tmp.py"
        environments = (
            {"GIT_DIR": str(foreign / ".git")},
            {"GIT_DIR": str(foreign / ".git"), "GIT_WORK_TREE": str(foreign),
             "GIT_COMMON_DIR": str(foreign / ".git")},
            {"GIT_COMMON_DIR": str(foreign / ".git")},
        )
        for number, environment in enumerate(environments):
            with self.subTest(environment=environment):
                scratch.mkdir(parents=True, exist_ok=True)
                sentinel = scratch / "keep"
                sentinel.write_text("keep")
                accepted = self.repo / f".codex/tmp/sibling-{number}"
                accepted.mkdir(parents=True)
                with patch.dict(os.environ, environment):
                    rejected = run([sys.executable, str(guard), "-w", str(sentinel)],
                                   cwd=target, check=False)
                    deletion = run([sys.executable, str(cleanup), str(scratch)],
                                   cwd=target, check=False)
                    self.assertEqual(rejected.returncode, 1)
                    self.assertEqual(deletion.returncode, 1)
                    self.assertEqual(sentinel.read_text(), "keep")
                    run([sys.executable, str(guard), "-w", str(accepted / "result")], cwd=target)
                    run([sys.executable, str(cleanup), str(accepted)], cwd=target)
                self.assertFalse(accepted.exists())

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

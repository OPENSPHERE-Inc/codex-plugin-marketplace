from __future__ import annotations

import json
import os
import runpy
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from test_helpers import CREVIEW_SCRIPTS, git, init_repo, run


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class ReviewDiffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex pr diff ")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()
        init_repo(self.repo)
        self.base = git(self.repo, "rev-parse", "HEAD").stdout.strip()

    def capture(self, mode="--pr"):
        output = ".codex/tmp/review/diff.txt"
        run([sys.executable, str(CREVIEW_SCRIPTS / "fetch_diff.py"),
             mode, self.base, "HEAD", output], cwd=self.repo)
        return (self.repo / output).read_text(encoding="utf-8")

    def test_pr_uses_base_attributes_and_exposes_exact_rename(self):
        git(self.repo, "mv", "tracked.txt", "renamed.txt")
        (self.repo / ".gitattributes").write_text("*.txt -diff\n")
        (self.repo / "new.txt").write_text("visible source\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "rename and attributes")
        diff = self.capture()
        self.assertIn("+visible source", diff)
        self.assertIn("+base", diff)
        self.assertIn("-base", diff)
        self.assertNotIn("rename from", diff)
        self.assertNotIn("=== Staged Changes", diff)

    def test_non_ascii_binary_empty_and_mode_changes_remain_visible(self):
        git(self.repo, "config", "core.quotePath", "true")
        (self.repo / "画像.png").write_bytes(b"\x89PNG\x00binary")
        (self.repo / "empty.txt").touch()
        git(self.repo, "add", ".")
        git(self.repo, "update-index", "--chmod=+x", "tracked.txt")
        git(self.repo, "commit", "-qm", "assets")
        for mode in ("--pr", "--range"):
            with self.subTest(mode=mode):
                diff = self.capture(mode)
                self.assertIn("画像.png", diff)
                self.assertIn("Binary files /dev/null and b/画像.png differ", diff)
                self.assertIn("empty.txt", diff)
                self.assertIn("new mode 100755", diff)

    def test_pr_shows_submodule_even_when_configuration_ignores_it(self):
        git(self.repo, "update-index", "--add", "--cacheinfo", f"160000,{self.base},vendor")
        git(self.repo, "commit", "-qm", "submodule base")
        self.base = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        (self.repo / ".gitmodules").write_text(
            '[submodule "vendor"]\n\tpath = vendor\n\turl = https://example.invalid/repo\n'
            '\tignore = all\n'
        )
        git(self.repo, "add", ".gitmodules")
        git(self.repo, "update-index", "--cacheinfo", f"160000,{self.base},vendor")
        git(self.repo, "config", "diff.ignoreSubmodules", "all")
        git(self.repo, "commit", "-qm", "submodule update")
        self.assertIn("+Subproject commit " + self.base, self.capture())

    def test_untracked_non_ascii_binary_path_is_not_escaped(self):
        (self.repo / "画像.png").write_bytes(b"\x89PNG\x00binary")
        output = ".codex/tmp/review/diff.txt"
        run([sys.executable, str(CREVIEW_SCRIPTS / "fetch_diff.py"), self.base, output],
            cwd=self.repo)
        self.assertIn("b/画像.png differ", (self.repo / output).read_text(encoding="utf-8"))
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only").stdout, "")

    def test_pr_rejects_git_without_attribute_source(self):
        with patch.object(sys, "path", [str(CREVIEW_SCRIPTS), *sys.path]):
            api = runpy.run_path(str(CREVIEW_SCRIPTS / "fetch_diff.py"))
        original = api["run"]

        def old_git(command, **kwargs):
            if any(arg.startswith("--attr-source=") for arg in command):
                raise api["GitError"]("unknown option: --attr-source")
            return original(command, **kwargs)

        with working_directory(self.repo), patch.dict(api["main"].__globals__, {"run": old_git}):
            result = api["main"](["--pr", self.base, "HEAD", ".codex/tmp/old/diff.txt"])
        self.assertEqual(result, 1)
        self.assertFalse((self.repo / ".codex/tmp/old/diff.txt").exists())


class PullRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = runpy.run_path(str(CREVIEW_SCRIPTS / "gh_pr.py"))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex pr checkout ")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()
        init_repo(self.repo)
        self.head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.output = self.repo / ".codex/tmp/pr"
        self.output.mkdir(parents=True)
        self.metadata = self.output / "pr.json"
        self.metadata.write_text(json.dumps({
            "url": "https://github.com/example/project/pull/7", "number": 7,
            "head_sha": self.head, "base_sha": self.head, "merge_base": self.head,
        }), encoding="utf-8")

    def checkout(self, trust=False):
        original_run = self.api["run"]

        def local_checkout(cmd, cwd=None, env=None, ok=(0,)):
            if cmd[:3] == ["gh", "pr", "checkout"]:
                return original_run(["git", "checkout", "--detach", self.head], cwd, env, ok)
            return original_run(cmd, cwd, env, ok)

        with working_directory(self.repo), patch.dict(
            self.api["cmd_checkout"].__globals__, {"run": local_checkout}
        ):
            result = self.api["cmd_checkout"](str(self.metadata), *(("--trust",) if trust else ()))
        target = Path(result["worktree_path"])
        self.assertEqual(git(target, "rev-parse", "HEAD").stdout.strip(), self.head)
        return target

    def test_sparse_checkout_excludes_nested_agent_files_and_preserves_config(self):
        paths = ("AGENTS.md", "nested/aGeNtS.Override.MD", ".codex/config.toml",
                 "nested/.AGENTS/skills/example/SKILL.md")
        for name in paths:
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("untrusted instructions\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "agent files")
        self.head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        data = json.loads(self.metadata.read_text())
        data["head_sha"] = self.head
        self.metadata.write_text(json.dumps(data))
        before = (self.repo / ".git/config").read_bytes()
        target = self.checkout()
        for name in paths:
            self.assertFalse((target / name).exists(), name)
        self.assertTrue((target / "tracked.txt").exists())
        self.assertEqual((self.repo / ".git/config").read_bytes(), before)
        with working_directory(self.repo):
            self.api["cmd_remove"](str(target))
        self.assertFalse(target.exists())
        trusted = self.checkout(trust=True)
        for name in paths:
            self.assertTrue((trusted / name).exists(), name)
        with working_directory(self.repo):
            self.api["cmd_remove"](str(trusted))

    def test_dirty_checkout_is_retained_and_foreign_worktree_is_rejected(self):
        target = self.checkout()
        (target / "tracked.txt").write_text("dirty\n")
        with working_directory(self.repo), self.assertRaises(self.api["Error"]):
            self.api["cmd_remove"](str(target))
        self.assertTrue(target.exists())
        foreign = self.repo / ".codex/worktrees/creview-pr-7-20000101-000000"
        git(self.repo, "worktree", "add", "--detach", str(foreign), "HEAD")
        with working_directory(self.repo), self.assertRaises(self.api["Error"]):
            self.api["cmd_remove"](str(foreign))
        self.assertTrue(foreign.exists())

    def test_checkout_and_removal_disable_hooks_filters_and_fsmonitor(self):
        hooks = self.repo / "hooks"
        hooks.mkdir()
        marker = self.repo / "executed.txt"
        command = f'echo unexpected >> "{marker.as_posix()}"'
        for name in ("post-checkout", "post-index-change"):
            script = hooks / name
            script.write_text("#!/bin/sh\n" + command + "\n")
            script.chmod(0o755)
        (self.repo / ".gitattributes").write_text("*.txt filter=evil\n")
        git(self.repo, "add", ".gitattributes")
        git(self.repo, "commit", "-qm", "attributes")
        self.head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        data = json.loads(self.metadata.read_text())
        data["head_sha"] = self.head
        self.metadata.write_text(json.dumps(data))
        git(self.repo, "config", "core.hooksPath", str(hooks))
        git(self.repo, "config", "core.fsmonitor", command)
        for operation in ("clean", "smudge"):
            git(self.repo, "config", f"filter.evil.{operation}", command + "; cat")
        target = self.checkout()
        with working_directory(self.repo):
            self.api["cmd_remove"](str(target))
        self.assertFalse(marker.exists())

    def prepare_linked_worktree_filters(self):
        (self.repo / ".gitattributes").write_text(
            "tracked.txt filter=linked-text\nprocessed.txt filter=linked-process\n"
        )
        (self.repo / "processed.txt").write_text("process input\n")
        (self.repo / "AGENTS.md").write_text("untrusted instructions\n")
        git(self.repo, "add", ".gitattributes", "processed.txt", "AGENTS.md")
        git(self.repo, "commit", "-qm", "linked worktree filters")
        self.head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        data = json.loads(self.metadata.read_text())
        data["head_sha"] = self.head
        self.metadata.write_text(json.dumps(data))

        marker = self.repo / "executed.txt"
        command = f'echo unexpected >> "{marker.as_posix()}"'
        hooks = self.repo / ".git/test-hooks"
        hooks.mkdir()
        for name in ("post-checkout", "post-index-change"):
            script = hooks / name
            script.write_text("#!/bin/sh\n" + command + "\n")
            script.chmod(0o755)
        git(self.repo, "config", "core.hooksPath", str(hooks))
        git(self.repo, "config", "core.fsmonitor", command)

        config = self.repo / ".git/linked-filters"
        for operation in ("clean", "smudge"):
            git(self.repo, "config", "--file", str(config),
                f"filter.linked-text.{operation}", command + "; cat")
        git(self.repo, "config", "--file", str(config),
            "filter.linked-process.process", command + "; exit 1")
        for driver in ("linked-text", "linked-process"):
            git(self.repo, "config", "--file", str(config), f"filter.{driver}.required", "true")
        return config, marker

    def enable_linked_worktree_filters(self, config):
        git(self.repo, "config", "includeIf.gitdir:**/.git/worktrees/**.path", config.as_posix())
        result = run(["git", "config", "--get", "filter.linked-text.smudge"],
                     cwd=self.repo, check=False)
        self.assertEqual(result.returncode, 1)

    def test_linked_worktree_filters_are_disabled_for_checkout(self):
        config, marker = self.prepare_linked_worktree_filters()
        self.enable_linked_worktree_filters(config)
        before = (self.repo / ".git/config").read_bytes()
        for trust in (False, True):
            with self.subTest(trust=trust):
                target = self.checkout(trust=trust)
                self.assertEqual((target / "tracked.txt").read_text(), "base\n")
                self.assertEqual((target / "processed.txt").read_text(), "process input\n")
                self.assertEqual((target / "AGENTS.md").exists(), trust)
                self.assertEqual(git(target, "config", "--get",
                                     "filter.linked-process.required").stdout.strip(), "true")
                self.assertFalse(marker.exists())
                with working_directory(self.repo):
                    self.api["cmd_remove"](str(target))
                self.assertFalse(marker.exists())
                self.assertEqual((self.repo / ".git/config").read_bytes(), before)

    def test_remove_disables_filters_enabled_only_in_linked_worktree(self):
        config, marker = self.prepare_linked_worktree_filters()
        target = self.checkout()
        self.enable_linked_worktree_filters(config)
        before = (self.repo / ".git/config").read_bytes()
        for name in ("tracked.txt", "processed.txt"):
            path = target / name
            os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 2))
        with working_directory(self.repo):
            self.api["cmd_remove"](str(target))
        self.assertFalse(target.exists())
        self.assertFalse(marker.exists())
        self.assertEqual((self.repo / ".git/config").read_bytes(), before)

    def test_failed_checkout_keeps_linked_filter_overrides_during_cleanup(self):
        config, marker = self.prepare_linked_worktree_filters()
        self.enable_linked_worktree_filters(config)
        data = json.loads(self.metadata.read_text())
        data["head_sha"] = "1" * 40
        self.metadata.write_text(json.dumps(data))
        before = git(self.repo, "worktree", "list", "--porcelain").stdout
        original_remove = self.api["remove_worktree"]
        original_run = self.api["run"]
        cleaned = []

        def cleanup(path, env):
            for driver in ("linked-text", "linked-process"):
                for operation in ("clean", "smudge", "process"):
                    self.assertEqual(original_run(
                        ["git", "config", "--get", f"filter.{driver}.{operation}"],
                        cwd=path, env=env,
                    ).strip(), "")
                self.assertEqual(original_run(
                    ["git", "config", "--get", f"filter.{driver}.required"], cwd=path, env=env,
                ).strip(), "false")
            cleaned.append(path)
            return original_remove(path, env)

        with patch.dict(self.api["cmd_checkout"].__globals__, {"remove_worktree": cleanup}):
            with self.assertRaisesRegex(self.api["Error"], "updated after fetch"):
                self.checkout()
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(git(self.repo, "worktree", "list", "--porcelain").stdout, before)
        self.assertFalse(marker.exists())

    def test_remove_retains_worktree_when_filter_configuration_cannot_be_read(self):
        target = self.checkout()
        original_run = self.api["run"]
        before = git(self.repo, "worktree", "list", "--porcelain").stdout

        def unreadable_config(cmd, cwd=None, env=None, ok=(0,)):
            if cmd[:3] == ["git", "config", "--name-only"] and Path(cwd or ".") == target:
                raise self.api["Error"]("cannot read linked worktree filters")
            return original_run(cmd, cwd, env, ok)

        with working_directory(self.repo), patch.dict(
            self.api["cmd_remove"].__globals__, {"run": unreadable_config}
        ), self.assertRaisesRegex(self.api["Error"], "cannot read linked worktree filters"):
            self.api["cmd_remove"](str(target))
        self.assertTrue(target.exists())
        self.assertEqual(git(self.repo, "worktree", "list", "--porcelain").stdout, before)

    def test_fetch_checks_url_remote_and_open_state_before_writes(self):
        with working_directory(self.repo):
            for url in ("https://github.com/example/project/issues/7",
                        "https://github.com/foreign/project/pull/7"):
                with self.assertRaises(self.api["Error"]):
                    self.api["cmd_fetch"](url, str(self.output))
        with working_directory(self.repo), patch.dict(self.api["cmd_fetch"].__globals__, {
            "is_remote": lambda *args: True,
            "run": lambda *args, **kwargs: json.dumps({"number": 7, "state": "MERGED"}),
        }), self.assertRaisesRegex(self.api["Error"], "not open"):
            self.api["cmd_fetch"]("https://github.com/example/project/pull/7", str(self.output))

    def test_fetch_writes_context_and_rejects_dirty_in_place_checkout(self):
        original = self.api["run"]
        pr = {"number": 7, "state": "OPEN", "headRefOid": self.head, "baseRefOid": self.head,
              "headRepository": {"name": "project"}, "headRepositoryOwner": {"login": "example"},
              "title": "Title", "body": "Description", "statusCheckRollup": []}

        def github(command, **kwargs):
            if command[:3] == ["gh", "pr", "view"]:
                return json.dumps(pr)
            if command[:2] == ["gh", "api"]:
                if "/compare/" in command[-1]:
                    return json.dumps({"merge_base_commit": {"sha": self.head}})
                return "[]"
            return original(command, **kwargs)

        with working_directory(self.repo), patch.dict(self.api["cmd_fetch"].__globals__, {
            "is_remote": lambda *args: True, "run": github,
        }):
            result = self.api["cmd_fetch"]("https://github.com/example/project/pull/7",
                                           str(self.output))
            self.assertTrue(result["in_place"])
            context = json.loads((self.output / "pr-context.json").read_text(encoding="utf-8"))
            self.assertEqual(context["title"], "Title")
            self.assertEqual(context["body"], "Description")
            self.assertNotIn("body", result)
            (self.repo / "tracked.txt").write_text("dirty\n")
            with self.assertRaisesRegex(self.api["Error"], "uncommitted"):
                self.api["cmd_fetch"]("https://github.com/example/project/pull/7", str(self.output))

    def test_conversation_caps_each_list_and_excludes_pending_reviews(self):
        entries = [{"id": i, "body": str(i), "state": "COMMENTED"} for i in range(60)]

        def pages(endpoint, host):
            if endpoint.endswith("/reviews"):
                return [*entries, {"id": 99, "state": "PENDING", "body": "private"}], True
            return entries, True

        with patch.dict(self.api["conversation"].__globals__, {"api_pages": pages}):
            result = self.api["conversation"]("github.com", "example/project", 7)
        self.assertTrue(result["omitted"])
        for key in ("reviews", "issue_comments", "review_comments"):
            self.assertEqual(len(result[key]), 50)
            self.assertEqual(result[key][0]["body"], "10")

    def test_remote_resolution_honors_rewrites_and_ssh_aliases(self):
        git(self.repo, "remote", "add", "origin", "short:example/project.git")
        git(self.repo, "config", "url.git@review-alias:.insteadOf", "short:")
        with working_directory(self.repo), patch.dict(self.api["is_remote"].__globals__, {
            "ssh_hostname": lambda alias: "ssh.github.com" if alias == "review-alias" else alias,
        }):
            self.assertTrue(self.api["is_remote"]("github.com", "Example", "Project"))
            self.assertFalse(self.api["is_remote"]("example.org", "example", "project"))

    def test_head_movement_rolls_back_the_created_worktree(self):
        data = json.loads(self.metadata.read_text())
        data["head_sha"] = "1" * 40
        self.metadata.write_text(json.dumps(data))
        before = git(self.repo, "worktree", "list", "--porcelain").stdout
        with self.assertRaisesRegex(self.api["Error"], "updated after fetch"):
            self.checkout()
        self.assertEqual(git(self.repo, "worktree", "list", "--porcelain").stdout, before)

    def test_exclusion_check_fails_closed(self):
        with patch.dict(self.api["check_agent_files_left_out"].__globals__, {
            "agent_file_left": lambda root: "nested/AGENTS.md",
        }), self.assertRaisesRegex(self.api["Error"], "still resolves"):
            self.api["check_agent_files_left_out"](str(self.repo), 7)

        def unreadable(root):
            raise PermissionError("cannot inspect")

        with patch.dict(self.api["check_agent_files_left_out"].__globals__, {
            "agent_file_left": unreadable,
        }), self.assertRaisesRegex(self.api["Error"], "could not be examined"):
            self.api["check_agent_files_left_out"](str(self.repo), 7)

    def test_ci_deduplicates_reruns_and_restricts_job_logs(self):
        def check(repo, run_id, job_id, started, conclusion):
            return {"name": "test", "workflowName": "CI", "startedAt": started,
                    "status": "COMPLETED", "conclusion": conclusion,
                    "detailsUrl": f"https://github.com/{repo}/actions/runs/{run_id}/job/{job_id}"}
        rollup = [check("example/project", 1, 10, "1", "FAILURE"),
                  check("example/project", 1, 11, "2", "SUCCESS"),
                  check("foreign/project", 2, 12, "3", "FAILURE"),
                  check("example/project", 3, 13, "4", "FAILURE")]
        calls = []
        with patch.dict(self.api["ci_checks"].__globals__, {
            "job_log_excerpt": lambda *args: calls.append(args) or "failure cause",
        }):
            result = self.api["ci_checks"](rollup, "github.com", {"example/project"})
        self.assertEqual(len(result), 3)
        self.assertEqual(calls, [("github.com", "example/project", "13")])
        self.assertEqual(result[-1]["log_excerpt"], "failure cause")

    def test_ci_preserves_same_named_external_checks(self):
        for workflow in (None, ""):
            with self.subTest(workflow=workflow):
                rollup = [
                    {"name": "test", "startedAt": "1", "status": "COMPLETED",
                     "conclusion": "FAILURE", "detailsUrl": "https://ci.example/failed/1"},
                    {"name": "test", "startedAt": "2", "status": "COMPLETED",
                     "conclusion": "SUCCESS", "detailsUrl": "https://ci.other/passed/2"},
                ]
                if workflow is not None:
                    for check in rollup:
                        check["workflowName"] = workflow
                with patch.dict(self.api["ci_checks"].__globals__, {
                    "job_log_excerpt": lambda *args: self.fail("external CI log requested"),
                }):
                    result = self.api["ci_checks"](rollup, "github.com", {"example/project"})
                self.assertEqual([check["conclusion"] for check in result],
                                 ["FAILURE", "SUCCESS"])
                self.assertEqual([check["url"] for check in result],
                                 [check["detailsUrl"] for check in rollup])

    def test_ci_keeps_actions_runs_from_different_hosts_and_repositories(self):
        sources = [("github.com", "example/project"),
                   ("github.com", "foreign/project"),
                   ("github.enterprise", "example/project")]
        rollup = [
            {"name": "test", "workflowName": "CI", "startedAt": str(index),
             "status": "COMPLETED", "conclusion": "FAILURE",
             "detailsUrl": f"https://{host}/{repo}/actions/runs/1/job/{index}"}
            for index, (host, repo) in enumerate(sources, 10)
        ]
        calls = []
        with patch.dict(self.api["ci_checks"].__globals__, {
            "job_log_excerpt": lambda *args: calls.append(args) or "failure cause",
        }):
            result = self.api["ci_checks"](rollup, "github.com", {"example/project"})
        self.assertEqual([check["url"] for check in result],
                         [check["detailsUrl"] for check in rollup])
        self.assertEqual(calls, [("github.com", "example/project", "10")])
        self.assertEqual(["log_excerpt" in check for check in result], [True, False, False])

    def test_ci_caps_failed_job_logs_without_omitting_checks(self):
        limit = self.api["MAX_JOB_LOGS"]
        rollup = [
            {"name": "test", "workflowName": "CI", "startedAt": "1",
             "status": "COMPLETED", "conclusion": "FAILURE",
             "detailsUrl": f"https://github.com/example/project/actions/runs/{index}/job/{index}"}
            for index in range(limit + 2)
        ]
        calls = []
        with patch.dict(self.api["ci_checks"].__globals__, {
            "job_log_excerpt": lambda *args: calls.append(args) or "failure cause",
        }):
            result = self.api["ci_checks"](rollup, "github.com", {"example/project"})
        self.assertEqual(len(result), limit + 2)
        self.assertEqual(calls, [("github.com", "example/project", str(index))
                                 for index in range(limit)])
        self.assertEqual(sum("log_excerpt" in check for check in result), limit)

    def test_ci_preserves_unstarted_attempts_and_their_entire_group(self):
        for conclusion in ("SUCCESS", "FAILURE"):
            for status in ("QUEUED", "WAITING"):
                for started in ({}, {"startedAt": None}, {"startedAt": ""}):
                    for reverse in (False, True):
                        with self.subTest(conclusion=conclusion, status=status,
                                          started=started, reverse=reverse):
                            base_url = "https://github.com/example/project/actions/runs/1/job/"
                            rollup = [
                                {"name": "test", "workflowName": "CI", "startedAt": str(index),
                                 "status": "COMPLETED", "conclusion": conclusion,
                                 "detailsUrl": base_url + str(index)}
                                for index in (10, 11)
                            ]
                            rollup.append({
                                "name": "test", "workflowName": "CI", "status": status,
                                "conclusion": None, "detailsUrl": base_url + "12", **started,
                            })
                            if reverse:
                                rollup.reverse()
                            calls = []
                            with patch.dict(self.api["ci_checks"].__globals__, {
                                "job_log_excerpt": lambda *args: calls.append(args) or "failure",
                            }):
                                result = self.api["ci_checks"](
                                    rollup, "github.com", {"example/project"},
                                )
                            self.assertEqual([check["url"] for check in result],
                                             [check["detailsUrl"] for check in rollup])
                            self.assertEqual([check["status"] for check in result],
                                             [check["status"] for check in rollup])
                            self.assertEqual([check["conclusion"] for check in result],
                                             [check["conclusion"] for check in rollup])
                            expected = [
                                ("github.com", "example/project",
                                 check["detailsUrl"].rsplit("/", 1)[1])
                                for check in rollup if check["conclusion"] == "FAILURE"
                            ]
                            self.assertEqual(calls, expected)

    def test_executable_lookup_ignores_worktree_and_relative_path_entries(self):
        name = "planted.exe" if os.name == "nt" else "planted"
        planted = self.repo / name
        planted.write_text("untrusted")
        planted.chmod(0o755)
        with working_directory(self.repo), patch.dict(os.environ, {"PATH": os.pathsep.join(("", "."))}):
            self.assertIsNone(self.api["executable"]("planted"))


if __name__ == "__main__":
    unittest.main()

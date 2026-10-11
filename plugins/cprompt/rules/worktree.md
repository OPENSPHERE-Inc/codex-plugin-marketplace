# Worktree and path contract

Apply before creating outputs or launching children. The calling skill fixes `timestamp` once.

## Initialization

- When a parent supplies `target_dir` and `main_root`, retain them and do not create another worktree.
- Otherwise require a Git repository root as the invocation directory. A nonempty `git rev-parse --show-prefix` is an error; stop before writes. Set absolute `target_dir` to `git rev-parse --show-toplevel` and `main_root = (none)`.
- With `--worktree[=branch]`, enable `--commit`. Without `=branch`, use `{skill-name}-{timestamp}`, where `skill-name` is `cdev-coding`, `creview-rounds`, or `cprompt-edit`. Reject an empty explicit branch.
- Only with `--worktree` and no inherited workspace, run `python "{plugin_root}/scripts/worktree.py" create "{branch}"` from the invocation root. Parse its JSON `{main_root, worktree_path, branch}`; set `target_dir = worktree_path` and retain ownership of this worktree. Existing local branches retain their tip; missing branches start at HEAD. A branch already checked out elsewhere is rejected.
- On creation failure, the helper retains registered targets because registration ownership cannot be verified, including after a clean hook failure. It reclaims only unregistered, empty directories whose reservation identity is verified, using `rmdir()`. Report the failed command, absolute retained path, requested branch, and retention reason, then stop without falling back to editing the original checkout. Do not treat the requested branch as the actual registered branch. Before retrying, resolve the cause, inspect the retained target, and explicitly remove it normally. Do not force removal or unconditionally delete retained targets automatically.
- Define `metadata_root = main_root` when it is not `(none)`, otherwise `target_dir`. Resolve the skill's scratch paths and relative document/output destinations against `metadata_root`, converting them to absolute paths before use. With a worktree, reject retained output destinations inside it.

## Execution and delegation

- Run source, Git, helper, format, build, and test commands with the execution tool's explicit `workdir = target_dir` (or equivalent). Confirm `git rev-parse --show-toplevel` there equals `target_dir`. A shell `cd` does not establish another tool call's or child's working directory.
- Resolve source paths against `target_dir`; use absolute paths for reads and edits. Preserve task-supplied paths: never rewrite an absolute path into the original checkout to point at the worktree. Such a path is read-only unless it is an assigned output.
- Pass absolute `plugin_root`, `target_dir`, `main_root` (or `(none)`), scratch paths, and output paths in every spawn and follow-up, including nested launches. Children use the same explicit execution directory and pass the contract on unchanged.
- Apply the target checkout's repository instructions. Discover project Codex profiles and `.codex/rules/` under `metadata_root`. Read fallback `AGENTS.md` / `README.md` build instructions from `target_dir`.
- Keep source writes within `target_dir`, and artifact writes within the assigned scratch/output paths. Reject `..` components and symlink escapes when checking containment; compare path components, treating Windows separators and drive-letter case equivalently. Task-specific read-only and edit-scope limits still apply.
- Exclude `.codex/tmp/`, `.codex/worktrees/`, and assigned report/design destinations from source staging. Preserve unrelated changes and pre-existing staged content. Worktree mode starts from committed files; it does not copy uncommitted changes, ignored dependencies, secrets, or submodule contents.

## Completion

Only the skill that created the worktree removes it. After all children finish and required commits and retained outputs are complete, run `python "{plugin_root}/scripts/worktree.py" remove "{worktree_path}"` with `workdir = main_root`, including on early termination. Never force removal: on refusal, keep the worktree and report its path and reason. Git removal also deletes ignored files inside it. Keep the branch, report its name and commit hashes, and do not merge or push it.

# creview

*[日本語版 README](README_ja.md)*

`creview` is an explicitly invoked, staged multi-agent code-review workflow
for Codex. It runs each stage with Codex collaboration operations.

## Skills

| Skill | Purpose |
| --- | --- |
| `$creview:start` | Select reviewers, review the requested scope in parallel, and create a review document. |
| `$creview:triage` | Challenge, adjudicate, classify, and estimate findings. |
| `$creview:respond` | Implement accepted fixes and update finding statuses. |
| `$creview:resolve` | Verify fixes against the source and record the result. |
| `$creview:rounds` | Compose the four stages for multiple rounds until the stop condition is met. |

Example:

~~~text
$creview:rounds .codex/tmp --base origin/main --max-rounds 3
~~~

`$creview:rounds` accepts the same input and output controls as the Claude
version, with `.codex/` replacing `.claude/`:

- An optional positional output base path; default `.codex/tmp/`.
- `--confirm`, `--confirm-round`, `--commit`, `--incremental`, `--adr`, and
  `--adversarial`, all OFF by default.
- `--max-rounds N`, default 10 with range 1–20.
- `--base {branch}`, defaulting to an existing `main`, then `master`.
- `--output-dir {path}` for earlier Codex calls; it selects the exact run
  directory instead of adding a branch directory to the positional base path.

Normal rounds re-review the whole branch diff, including working-tree changes,
and do not require commits. `--incremental` reviews only the commits added by
the preceding round and therefore also enables `--commit`.

From Round 2 onward, a divergence gate runs after triage when fix targets exist.
It detects chains where past fixes cause new findings without shrinking across
at least three rounds, or demands to revert or contradict a past fix. When detected,
a specialist writes the root causes and fix proposals to `divergence-round{N}.md`.
The workflow presents that report and waits for an instruction to continue regardless
of `--confirm`, combining it with estimate confirmation when both apply.
A fix policy supplied with continuation also applies to that round's feedback fixes.

## Execution model

- The root agent remains the workflow leader.
- Independent reviewers are started with Codex collaboration tools.
- Work beyond the available slot count is queued.
- One-shot reviewers return structured JSONL and are not reused.
- Reviewer and divergence-investigator profiles can be discovered from project or
  user Codex agent configuration. Bundled reference profiles provide a fallback.

## Output

By default, `$creview:start` writes
`.codex/tmp/creview-start-{timestamp}.md`. `$creview:rounds` writes
`.codex/tmp/{branch-path}/review-round{N}.md` and `final-report.md`; repeat runs
append the lowest unused `_N` suffix to the branch name. Rounds with detected
divergence also save `divergence-round{N}.md` in that directory. An explicit
output path or rounds base path may place review documents elsewhere.

Temporary prompts, JSONL responses, and diff artifacts stay below
`.codex/tmp/`. The helper scripts reject temporary paths that escape the
scratch root.

Python helper scripts support diff capture, JSONL validation, document
rendering, and phase result compilation.

## Requirements

- Git repository
- Python 3.11 or later
- Codex collaboration tools
- Enough available collaboration slots for the requested parallelism

## Worktree execution

`$creview:rounds --worktree[=branch]` creates a separate checkout under
`.codex/worktrees/` and enables `--commit`. An existing branch starts at its tip; a missing
branch starts at the current HEAD. Without a branch name, it creates
`creview-rounds-{timestamp}`. A branch already checked out elsewhere is rejected.
The invocation checkout may contain uncommitted changes; those changes are not copied.

Relative source paths resolve against the worktree. Absolute paths into the original checkout
are read-only references and are not rewritten. Documents and scratch files stay in the invocation
checkout; relative output destinations resolve there too. Retained documents cannot be placed
inside the worktree. Project Codex profiles and `.codex/rules/` are read from the invocation
checkout.

At completion the worktree is removed and the branch is retained. If uncommitted changes or
another condition prevent removal, the worktree is kept and its path is reported. Removal also
deletes ignored files inside it. The workflow does not merge or push the branch.

Ignored dependencies, virtual environments, generated files, `.env`, and submodule contents are
not copied into a worktree. Verification must work in a fresh checkout. Configure runs only at
the start of the build stage, so it cannot prepare the earlier formatter or tests without a build.
Failures caused solely by missing prerequisites stop source-fix attempts and are reported as
environmental. For mixed failures, only code-caused errors are sent for source fixes.
With `--commit`, this run's fixes are committed even after reporting a verification failure.
Start all CReview skills from the repository root.

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

Each review document carries its round number. The final report includes accepted findings
left without a fix status when the loop ends, as well as recommendations for separate work.

## Reviewing a pull request

~~~text
$creview:start https://github.com/owner/repository/pull/123
~~~

PR mode requires Git 2.41 or later and authenticated `gh` access. The PR must be open and
its host, owner, and repository must match a remote of the current clone. A PR URL cannot
be combined with `--base` or `--range`. The review covers the merge base through the PR head;
rename detection is disabled, submodule changes remain visible, and attributes come from the
merge base. A failed diff capture stops the review in every mode.

If the checkout is already at the PR head, it is reviewed in place; tracked uncommitted
changes outside scratch paths stop the run. Otherwise, start creates a detached worktree under
`.codex/worktrees/`. It disables Git hooks, fsmonitor, and filter drivers, skips LFS smudging,
and checks symlinks out as plain files. The worktree is removed when the review ends;
dirty worktrees or cleanup failures are retained and reported. No branch is created.

By default, this worktree excludes `AGENTS.md`, `AGENTS.override.md`, `.codex`, `.agents`,
and `.mcp.json`, including nested and differently cased names. Their changes are reviewed
from the diff. `$creview:start ... --trust` also checks these files out; this option must
come from the user's own request. For agent configuration inspection with files present,
use `--trust` or an in-place review in a sandbox.

A dedicated description reviewer checks code against the PR's title, description, and CI
results. Failed GitHub Actions jobs can carry log excerpts; reruns are deduplicated and
job logs are fetched only from the PR's own repositories. Comments and reviews provide
context, with at most 50 entries per list. Every finding is anchored in changed code and
includes the relevant description or CI evidence. Pending checks, unrelated failures, and
comments themselves are not findings. The report retains the untranslated header marker
`- **PR:** {url} (head {sha}, base {sha})`; later phases do not yet interpret this marker.

`$creview:rounds` does not accept a PR URL. When a parent flow invokes start in PR mode,
it owns the checkout, which must already be at the PR head. This is separate from the
`$creview:rounds --worktree` option.

PR text and checked-out files are review data. Review agents do not execute PR worktree
code or write to remotes. The description reviewer's tool limits are prompt constraints;
Codex collaboration does not enforce a separate tool allowlist for this reference profile.
The workflow assumes the user has assessed and trusts the repository and PR. File exclusion
and helper safeguards support that decision; sandbox and permission settings remain the
execution boundary. In-place reviews retain existing agent configuration and environment
automation; `--trust` does not grant execution or remote-write authority.

## Changes without text hunks

Every changed file is assigned to reviewers in every start mode, including binary additions,
updates or deletions, mode changes, empty files, and renames. An empty review document is
produced only when no file changed. Scope file limits apply to these changes too.

Reviewers select perspectives from a file's uses as well as its extension. They can inspect
an image with an available image-viewing tool; deleted or unsupported binary formats are
judged from their uses. Inability to display a genuine binary is not itself a finding.
Findings about changes without lines use line 1.

A source, script, configuration, lockfile, or Markdown file shown as binary must still be
reviewed as text, including extensionless files identified by their uses. Reviewers inspect
the whole file and report when changed lines cannot be located or the content cannot be
fully read. A changed agent file excluded from a PR worktree and shown only as binary is
reported as unreviewable. Text classified as binary by NUL bytes or attributes still has
no changed-line diff; forcing a text diff remains a follow-up. Under `--range`, file inspection
uses the current checkout, which may differ from the range's end revision.

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

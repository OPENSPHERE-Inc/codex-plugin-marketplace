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

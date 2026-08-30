# creview

*[日本語版 README](README_ja.md)*

`creview` is an explicitly invoked, staged multi-agent code-review workflow
for Codex. It replaces Claude-specific background tasks and
`agent-sequencer` with Codex collaboration operations.

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
- `--max-rounds N`, default 5 with range 1–10.
- `--base {branch}`, defaulting to an existing `main`, then `master`.
- `--output-dir {path}` for earlier Codex calls; it selects the exact run
  directory instead of adding a branch directory to the positional base path.

Normal rounds re-review the whole branch diff, including working-tree changes,
and do not require commits. `--incremental` reviews only the commits added by
the preceding round and therefore also enables `--commit`.

## Execution model

- The root agent remains the workflow leader.
- Independent reviewers are started with Codex collaboration tools.
- Work beyond the available slot count is queued.
- One-shot reviewers return structured JSONL and are not reused.
- Reviewer profile metadata can be discovered from project or user Codex agent
  configuration. Bundled reference profiles provide a fallback.

The workflow never assumes a named Claude subagent type and does not require an
external sequencer plugin.

## Output

By default, `$creview:start` writes
`.codex/tmp/creview-start-{timestamp}.md`. `$creview:rounds` writes
`.codex/tmp/{branch-path}/review-round{N}.md` and `final-report.md`; repeat runs
append the lowest unused `_N` suffix to the branch name. An explicit output
path or rounds base path may place review documents elsewhere.

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

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
$creview:rounds Review the changes relative to origin/main, run up to 3 rounds,
and stop early when no actionable finding remains.
~~~

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

Review state is stored below `.codex/reviews/` in the repository being
reviewed. Temporary prompts, JSONL responses, and diff artifacts stay below
`.codex/tmp/`. The scripts reject paths that escape the scratch root.

Python helper scripts support diff capture, JSONL validation, document
rendering, and phase result compilation.

## Requirements

- Git repository
- Python 3.11 or later
- Codex collaboration tools
- Enough available collaboration slots for the requested parallelism

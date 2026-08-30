---
name: rounds
description: Run explicitly requested bounded CReview rounds by composing start, triage, respond, and resolve until no further authorized code change occurs. Do not activate for an ordinary review request.
---

# Multi-Round Review

Coordinate the four CReview phase skills in the root agent. Do not create phase-leader agents; each phase already owns its sub-agent delegation.

## Runtime paths

Resolve this skill's absolute directory and `plugin_root`. Read the sibling skill files before executing their phase:

- `../start/SKILL.md`
- `../triage/SKILL.md`
- `../respond/SKILL.md`
- `../resolve/SKILL.md`

## Input and options

Accept an optional positional output base path. When omitted, use `.codex/tmp/` in the project root.

Options:

- `--confirm` (default OFF) — After triage and estimate are persisted, show the estimate summary and wait for the user before respond.
- `--confirm-round` (default OFF) — After resolve, wait for the user before the next round when unresolved findings remain.
- `--commit` (default OFF) — Forward to respond.
- `--incremental` (default OFF) — From Round 2 onward, review only the committed range from the previous round's starting revision through the current round's starting revision instead of the whole branch. This option also enables `--commit`.
- `--adr` (default OFF) — Allow triage or respond to create an ADR beside the review document for a durable design decision. Existing ADRs referenced by the review document are read and updated during fixes regardless of this option.
- `--max-rounds N` — Default 5, range 1–10.
- `--base {branch}` — Review base. Otherwise use an existing `main`, then `master`. `--incremental` replaces this with a revision range from Round 2 onward.
- `--adversarial` (default OFF) — Forward to start.
- `--output-dir {path}` — Compatibility option for earlier Codex releases. Use the path as the exact run directory without branch-directory selection. If combined with the positional argument, stop and report the conflict.

## Review documents

Unless `--output-dir` is set, obtain the current branch with `git branch --show-current` at startup and choose the run directory once:

- The first run uses `{base-path}/{branch-name}/`, preserving `/` in the branch name as directory hierarchy.
- If that branch directory exists, append `_1`, `_2`, and so on to the branch name, choosing the lowest unused number.
- Example: the first run for `feat/add-replay` uses `{base-path}/feat/add-replay/`; the next uses `{base-path}/feat/add-replay_1/`.
- Each round uses `{run-dir}/review-round{N}.md`; the final report uses `{run-dir}/final-report.md`.

Write review documents and the final report in the user's language.

## Round workflow

1. Initialize options, the run directory, round counter `1`, and `prev_round_rev = (none)`. Never require a clean worktree; preserve unrelated user changes.
2. At the start of each round, record `git rev-parse HEAD` as `this_round_rev` and choose the review target:
   - With `--incremental` OFF, or in Round 1, use `--base` without a revision range. Later rounds re-review the whole branch diff, including committed and working-tree changes.
   - With `--incremental` ON from Round 2 onward, use `prev_round_rev..this_round_rev`. If the revisions are equal, stop the round loop because no new commit exists.
3. Run `start` with explicit output `{run-dir}/review-round{N}.md` and the selected base or range.
4. Run `triage` on that document, passing all earlier round-document paths as prior-round context.
5. If `--confirm` is set, show the estimate summary and wait for the user before fixing Maintain or Alternative targets.
6. When Maintain or Alternative targets exist, run `respond` with the ADR and commit options. Otherwise skip it.
7. Run `resolve`. When Feedback remains, repeat triage → respond → resolve for that document up to three feedback attempts.
8. Record findings, decisions, fixes, verification counts, workflow warnings, `this_round_rev`, feedback attempts, and `code_changed`.
9. Start another round only when `code_changed` is true and the current round number is below `--max-rounds`. If unresolved findings remain and `--confirm-round` is set, wait for the user first. On continuation, set `prev_round_rev = this_round_rev` and increment the round number. `--commit` is not a continuation requirement in normal mode.

## Final report

Spawn one aggregator with `templates/final-report-compile.md`, bundled profile `../../references/agents/review-helper.md`, expected ID `4f8a2d1c-9b35-4e67-a2c1-8b5d3f9e7a16`, all round document paths and statistics, `templates/final-report.md`, final path `{run-dir}/final-report.md`, and the user's language. Verify the returned path exists.

Report the final path, number of rounds, total findings, fixed/resolved/unresolved counts, and any stopped condition or workflow warning.

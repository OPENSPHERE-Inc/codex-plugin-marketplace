---
name: rounds
description: Run explicitly requested bounded CReview rounds by composing start, triage, respond, and resolve until no further authorized code change occurs. Do not activate for an ordinary review request.
---

# Multi-Round Review

Coordinate the four CReview phase skills in the root agent. Do not create phase-leader agents; each phase already owns its sub-agent delegation.

## Runtime paths and options

Resolve this skill's absolute directory and `plugin_root`. Read the sibling skill files before executing their phase:

- `../start/SKILL.md`
- `../triage/SKILL.md`
- `../respond/SKILL.md`
- `../resolve/SKILL.md`

Options:

- `--max-rounds N` — Default 2, range 1–5.
- `--base {branch}` — Review base.
- `--output-dir {path}` — Default `.codex/reviews/creview-rounds-{branch}-{timestamp}`.
- `--adversarial`, `--adr` — Forward to applicable phases.
- `--commit` — Forward to respond. More than one review round requires commits so later rounds have a stable revision boundary.
- `--confirm` — Pause after triage before respond.
- `--confirm-round` — Pause before another round when feedback or unresolved findings remain.

## Round workflow

1. Record the starting revision and create the output directory. Never require a clean worktree for review; preserve unrelated user changes.
2. For each round, run the `start` workflow with an explicit output `round-{N}.md`. Round 1 reviews the requested target. Later rounds review the previous round's committed revision through current `HEAD`.
3. Run `triage` on that document, passing all earlier round documents as prior-round context.
4. If `--confirm` is set, show the estimate summary and wait for the user before any fix.
5. When Maintain or Alternative targets exist, run `respond` with forwarded ADR and commit options. Otherwise skip it.
6. Run `resolve`. When Feedback remains, repeat triage → respond → resolve for that document up to three feedback attempts.
7. Record findings, decisions, fixes, verification counts, workflow warnings, revisions, and feedback attempts.
8. Start another round only when the round changed code, `--commit` produced a new `HEAD`, and the round limit permits it. Without `--commit`, stop after the current round and state that further rounds need a stable committed boundary.

## Final report

Spawn one aggregator with `templates/final-report-compile.md`, bundled profile `../../references/agents/review-helper.md`, expected ID `4f8a2d1c-9b35-4e67-a2c1-8b5d3f9e7a16`, all round document paths and statistics, `templates/final-report.md`, final path `{output_dir}/final-report.md`, and the user's language. Verify the returned path exists.

Report the final path, number of rounds, total findings, fixed/resolved/unresolved counts, and any stopped condition or workflow warning.

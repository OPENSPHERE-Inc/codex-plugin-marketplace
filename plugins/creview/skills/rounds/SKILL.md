---
name: rounds
description: Run explicitly requested bounded CReview rounds by composing start, triage, respond, and resolve until no further authorized code change occurs. Do not activate for an ordinary review request.
---

# Multi-Round Review

Coordinate the four CReview phase skills in the root agent. Do not create phase-leader agents; each phase already owns its sub-agent delegation.

## Runtime paths

Resolve this skill's absolute `skill_dir` and `plugin_root`, and read `../../rules/sub-agent.md`. Read the sibling skill files before executing their phase:

- `../start/SKILL.md`
- `../triage/SKILL.md`
- `../respond/SKILL.md`
- `../resolve/SKILL.md`

## Input and options

Accept an optional positional output base path. When omitted, use `.codex/tmp/` in the project root.

Options:

- `--confirm` (default OFF) — After triage and estimate are persisted, show the estimate summary and wait for the user's instruction to continue before respond.
- `--confirm-round` (default OFF) — Wait for the user's instruction to continue before starting the next round.
- `--commit` (default OFF) — Forward to respond.
- `--incremental` (default OFF) — From Round 2 onward, review only the committed range from the previous round's starting revision through the current round's starting revision instead of the whole branch. This option also enables `--commit`.
- `--adr` (default OFF) — Allow triage or respond to create an ADR beside the review document for a durable design decision. Existing ADRs referenced by the review document are read and updated during fixes regardless of this option.
- `--max-rounds N` — Default 10, range 1–20.
- `--base {branch}` — Review base. Otherwise use an existing `main`, then `master`. `--incremental` replaces this with a revision range from Round 2 onward.
- `--adversarial` (default OFF) — Forward to start.
- `--output-dir {path}` — Compatibility option for earlier Codex releases. Use the path as the exact run directory without branch-directory selection. If combined with the positional argument, stop and report the conflict.

## Review documents

Unless `--output-dir` is set, obtain the current branch with `git branch --show-current` at startup and choose the run directory once:

- The first run uses `{base-path}/{branch-name}/`, preserving `/` in the branch name as directory hierarchy.
- If that branch directory exists, append `_1`, `_2`, and so on to the branch name, choosing the lowest unused number.
- Example: the first run for `feat/add-replay` uses `{base-path}/feat/add-replay/`; the next uses `{base-path}/feat/add-replay_1/`.
- Each round uses `{run-dir}/review-round{N}.md`; the final report uses `{run-dir}/final-report.md`.

Write divergence investigation reports to `{run-dir}/divergence-round{N}.md`. Write review documents and all reports in the user's language.

## Round workflow

1. Initialize options, the run directory, round counter `1`, `prev_round_rev = (none)`, round-specific overrides `(none)`, `divergence_count = 0`, and `report_path = null`. Never require a clean worktree; preserve unrelated user changes.
2. At the start of each round, record `git rev-parse HEAD` as `this_round_rev` and choose the review target:
   - With `--incremental` OFF, or in Round 1, use `--base` without a revision range. Later rounds re-review the whole branch diff, including committed and working-tree changes.
   - With `--incremental` ON from Round 2 onward, use `prev_round_rev..this_round_rev`. If the revisions are equal, stop the round loop because no new commit exists.
3. Run `start` with explicit output `{run-dir}/review-round{N}.md` and the selected base or range.
4. Run `triage` on that document, passing all earlier round document paths as previous-round context. On `error`, run no further phase, record the results in step 9, and proceed to the final report.
5. From Round 2 on, when `will_fix_count >= 1` and `maintain_count + alternative_count >= 1`, run the divergence gate below. Do not run it inside the feedback loop.
6. When divergence is detected, read `report_path` and present its content. When `--confirm` is set and Maintain / Alternative targets exist, present triage's `summary`. If either condition applies, present the applicable information together and wait once for the user's instruction to continue. Divergence confirmation does not depend on `--confirm`.
   - If the user instructs a stop, run no further phase, record the results in step 9, and proceed to the final report without starting another round.
   - If the user supplies a fix policy along with continuation, retain it verbatim with the reference `report_path` (null when no report exists) as this round's `respond` override. Continuation alone does not adopt the recommended proposal.
7. Run `respond` with the ADR and commit options and this round's override when Maintain or Alternative targets exist; otherwise skip only `respond`. Proceed to `resolve` in either case to verify Won't Fix and Downgrade findings too.
8. Run `resolve`. If Feedback remains, repeat triage, respond only when targets exist, and resolve on that document for at most three feedback attempts. Resend the user's fix policy and `report_path` to every `respond`. Apply step 6 to `--confirm` and stop instructions, but do not repeat the divergence pause. Run `resolve` in every attempt unless triage errors or the user instructs a stop.
9. Record finding, decision, fix, and verification counts; workflow warnings; `this_round_rev`; and feedback attempts. Counts for phases that did not run are 0. Set `code_changed` to the logical OR of all `respond` return values in this round, or false if it never ran.
10. Start another round only when there is no error or user stop instruction, `code_changed` is true, and the current round number is below `--max-rounds`. If `--confirm-round` is set, wait for the user's instruction to continue before starting the next round; on a stop instruction, proceed to the final report. On continuation, set `prev_round_rev = this_round_rev`, increment the round number, and reset round-specific overrides and divergence results. `--commit` is not a continuation requirement in normal mode.

## Divergence gate

Triage deletes its temporary directory at phase completion, so create a dedicated `gate_tmp_dir` at `.codex/tmp/creview-divergence-{timestamp}-round{N}/`. Set `timestamp` once at run startup. Keep only paths, counts, and the selected profile in root context, not intermediate result bodies.

1. Spawn one detection agent with `templates/divergence-check.md`, bundled profile `../../references/agents/review-helper.md`, and expected ID `6570a998-e9f3-4421-af84-6911eebd7c07`. Variables: `plugin_root`, `document_path`, `previous_round_doc_paths`, and `output_path = {gate_tmp_dir}/divergence.jsonl`. Return value: `{divergence_count, investigator, template_id}`.
2. When `divergence_count >= 1`, confirm the detection file exists and spawn one investigation agent with `templates/divergence-investigate.md`, the selected `investigator.profile_path` (a general agent without a profile when null), and expected ID `ad54f81e-81f1-43c0-acff-0941524b8a3e`. Variables: `plugin_root`, `divergence_path = {gate_tmp_dir}/divergence.jsonl`, `document_path`, `previous_round_doc_paths`, `template_path = {skill_dir}/templates/divergence-report.md`, `report_path = {run-dir}/divergence-round{N}.md`, and `language`. The same agent investigates all divergences. Confirm the returned `report_path` exists.
3. After detection and any required investigation succeed, delete only the dedicated temporary directory with `python "{plugin_root}/scripts/del_tmp.py" {gate_tmp_dir}` and return to the round's confirmation step. Zero divergences require neither investigation nor a divergence pause. Report missing outputs or agent failures, record the round's results, and proceed to the final report without running fixes.

Use `(none)` overrides for both agents. Follow `sub-agent.md` for launch messages, template ID validation, and concurrency limits.

## Final report

Spawn one aggregator with `templates/final-report-compile.md`, bundled profile `../../references/agents/review-helper.md`, expected ID `4f8a2d1c-9b35-4e67-a2c1-8b5d3f9e7a16`, all round document paths and statistics, `templates/final-report.md`, final path `{run-dir}/final-report.md`, and the user's language. Verify the returned path exists.

Report the final path, number of rounds, total findings, fixed/resolved/unresolved counts, and any stopped condition or workflow warning.

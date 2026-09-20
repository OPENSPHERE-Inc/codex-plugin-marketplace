---
name: triage
description: Adversarially triage findings in an existing CReview document, estimate accepted work, and persist triage and estimate metadata. Use when the user explicitly invokes this CReview phase or requests multi-agent review triage.
---

# Review Triage and Estimate

Treat the review document as the handoff boundary. Do not fix source code in this phase.

## Runtime paths

Resolve `skill_dir` from this loaded file and `plugin_root` two levels above it; use absolute values in child messages. Read `../../rules/sub-agent.md`. This phase requires collaboration tools and may use nested challenge agents; stop when delegation is unavailable.

## Input and options

- Required: path to a CReview document.
- `--adr` — Allow an estimate agent to create or update an ADR for a lasting design decision.
- An upper workflow may provide prior-round document paths and phase overrides.

Fix `{timestamp}` once and create `.codex/tmp/creview-triage-{timestamp}/estimates/`.

## Workflow

1. Spawn `triage_primary_{timestamp}` with `templates/triage.md`, expected `template_id` `1e9c4f7a-5b82-4d63-a1c8-3f7d2e9b4a15`, and variables `plugin_root`, `document_path`, `tmp_dir`, and `previous_round_doc_paths`. The template performs propose, independent challenges, majority-gated adjudication, and writes `triage.jsonl`. Wait for `{path, will_fix_count, wontfix_count, flipped_count, by_stage, by_assignee, template_id}`.
2. On an `error` return, clean the run directory and stop without changing the review document.
3. For each Will-Fix `by_assignee` group, spawn an estimate agent with `templates/estimate.md`, expected ID `8b2d5f1c-7a93-4e64-b8d1-2c5e9a3f7b48`. Pass the IDs, document, run directory, ADR flag, timestamp, and the group's specialist profile path. Queue agents to respect the concurrency limit. Each agent writes `estimates/{id}.jsonl` and returns item IDs, verdicts, and ADR paths only.
4. When estimates exist, spawn `estimate_summary_{timestamp}` with `templates/estimate-summary.md`, bundled profile `../../references/agents/review-helper.md`, and expected ID `5c1e9b7a-3d48-4a96-b8e2-7f3c5a1d4b29`.
5. Run `python "{skill_dir}/scripts/compile-review.py" {tmp_dir} {document_path}`. This compiles `triage.jsonl` and estimate JSONL into `events.jsonl`, invokes the renderer, and persists only `triage` and `estimate` metadata.
6. Confirm the compile command succeeded, retain its summary and counts, and remove the run directory with `python "{plugin_root}/scripts/del_tmp.py" {tmp_dir}`.

Never add `status` or `verification` in this phase. Preserve structural labels and emoji exactly. Report counts, the document path, any ADR paths, and that `$creview:respond` is the next phase.

Return to a parent workflow `{document_path, will_fix_count, wontfix_count, flipped_count, maintain_count, alternative_count, downgrade_count, summary, error}`. Estimate counts are 0 when estimation did not run; `error` is null on success. `summary` contains the estimate summary text retained before temporary-directory cleanup (an empty string when no estimate exists), not a path to a deleted file. Return the failure reason in `error` on failure.

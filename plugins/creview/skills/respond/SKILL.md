---
name: respond
description: Fix Maintain and Alternative findings already persisted by CReview triage, run comment and build verification, and persist fix status. Use when the user explicitly invokes the CReview respond phase.
---

# Review Response

Read decisions from the review document. Do not assume a temporary directory shared with `$creview:triage`.

## Runtime paths and options

Resolve absolute `skill_dir` and `plugin_root` as in the other CReview skills and read `../../rules/sub-agent.md`.

- Required: review document path.
- `--adr` — Let fix agents read ADRs named by estimate metadata.
- `--commit` — After verification, stage only files recorded by this phase and create one concise commit. Never infer commit authorization without this option.

Create `.codex/tmp/creview-respond-{timestamp}/statuses/`.

## Workflow

1. Spawn `select_fix_targets_{timestamp}` with `templates/select-fix-targets.md`, expected ID `7c3e9a1d-5b48-4f62-9a8c-2d6f1b3e7a95`, and variables `plugin_root`, `document_path`, and `tmp_dir`. It writes `targets.jsonl` and returns `{fix_count, by_assignee}`.
2. If no targets exist, skip source-changing steps and continue to compilation.
3. Resolve each assignee to a Codex specialist profile with `../../rules/agents-detection.md`. Spawn one fix agent per group using `templates/fix.md`, expected ID `2f8a1c5d-7b94-4e63-a1c8-5d3f9b2e7a14`. Pass IDs, document, temp path, ADR flag, timestamp, and profile path. Queue beyond the available slots. Agents write `statuses/{id}.jsonl`.
4. Capture the current fix diff with `python "{plugin_root}/scripts/fetch_diff.py" HEAD {tmp_dir}/changes.txt`. Spawn `comment_review_{timestamp}` with `templates/comment-review.md`, bundled profile `../../references/agents/comment-sensei.md`, and expected ID `4a8e2d6f-9b15-4c73-8a2d-7f1e5c9b3d68`.
5. Run the format/build/test verification loop up to five attempts. Spawn `format_build_{timestamp}_{attempt}` with `templates/format-build-verify.md`, bundled profile `../../references/agents/review-helper.md`, and expected ID `9d3c5f8a-2b71-4e94-a8c5-1f7d3b9e2c46`. On failure, read only the operational failure fields from `format-build-result.jsonl`, resolve a specialist profile, and spawn `build_fix_{timestamp}_{attempt}` with `templates/build-fix.md`, expected ID `6e2a9f5c-1d83-4b74-9c2e-5a8d3f1b7e29`. Re-capture the diff before the next verification.
6. If `--commit` is set, stage only paths listed in this run's status files, excluding the review document and `.codex/tmp`, then create one commit. Do not use `git add -A`.
7. Run `python "{skill_dir}/scripts/compile-review.py" {tmp_dir} {document_path}` to persist `status` metadata. Confirm success, then remove the run directory with `python "{plugin_root}/scripts/del_tmp.py" {tmp_dir}`.

Report fixed count, changed files, verification result, commit hash when applicable, workflow warnings, and the document path. A build failure remains visible and is never described as success.

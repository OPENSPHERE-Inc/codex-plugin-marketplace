---
name: resolve
description: Verify fixes recorded in a CReview document against the current diff and persist Verified or Feedback metadata. Use when the user explicitly invokes the CReview resolve phase.
---

# Review Resolution

Verify findings; do not implement new fixes in this phase.

## Runtime paths and input

Resolve absolute `skill_dir` and `plugin_root` and read `../../rules/sub-agent.md`. The input is a CReview document plus optional `--base {branch}`; otherwise choose existing `main`, then `master`.

Create `.codex/tmp/creview-resolve-{timestamp}/verifications/`.

## Workflow

1. Capture the current review diff with `python "{plugin_root}/scripts/fetch_diff.py" {base} {tmp_dir}/diff.txt`.
2. Spawn `resolve_analysis_{timestamp}` with `templates/analyze.md`, bundled profile `../../references/agents/review-helper.md`, expected ID `5d9e2c8a-1f74-4b63-a9d8-3c5f7e1b9a42`, and variables `plugin_root` and `document_path`. Wait for `{total, by_assignee, template_id}`.
3. Resolve each assignee to a profile, then spawn verification agents with `templates/verify.md`, expected ID `8a1f5c9b-2e73-4d64-9c1e-8b3d7f2a5e94`. Pass assigned IDs, document, temp path, diff path, and profile. Queue beyond the available slots. Each agent writes `verifications/{id}.jsonl` and returns IDs and outcomes only.
4. Run `python "{skill_dir}/scripts/compile-review.py" {tmp_dir} {document_path}`. It produces `resolve-summary.md`, renders `verification` metadata, and returns counts.
5. Confirm compilation succeeded and remove the run directory with `python "{plugin_root}/scripts/del_tmp.py" {tmp_dir}` after retaining the short summary. Read the detailed summary only when needed for the user response.

Preserve `✅ Verified` and `💬 Feedback` values exactly. Report resolved, feedback, and unresolved counts plus the document path.

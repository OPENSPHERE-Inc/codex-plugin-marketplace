---
name: start
description: Run an explicitly requested parallel or multi-agent code review and consolidate findings into a structured review document. Do not activate for an ordinary single-agent review unless the user asks for CReview or parallel delegation.
---

# Parallel Code Review

Act as the review leader. Delegate review judgments and aggregation; retain only paths, counters, and short summaries.

This workflow requires Codex collaboration tools. Stop and report the missing capability when `spawn_agent`, `wait_agent`, or agent-status inspection is unavailable.

## Runtime paths

Resolve `skill_dir` from this loaded `SKILL.md` and `plugin_root` as two directory levels above it. Convert both to absolute paths before launching children. Read `../../rules/sub-agent.md`; every child launch follows that contract.

## Input and options

The review target may be paths, a branch, a revision range, a pull-request checkout, or a described subsystem.

- `--base {branch}` — Base branch; otherwise prefer an existing `main`, then `master`.
- `--range {from}..{to}` — Review only that committed range and omit working-tree changes.
- `--output {path}` — Review document path. Default: `.codex/reviews/creview-start-{timestamp}.md`.
- `--adversarial` — Use `templates/adversarial-reviewer.md`; otherwise use `templates/reviewer.md`.
- An optional round number is reflected in the document title.

Fix `{timestamp}` once as `YYYYMMDD-HHMMSS`. Write finding prose in the user's language while preserving the structural headings `Critical`, `Major`, `Minor`, `Info`, finding IDs, and `METADATA` markers.

## Workflow

1. Create `.codex/tmp/creview-start-{timestamp}/` and the parent of the final document.
2. Capture the review input with `python "{plugin_root}/scripts/fetch_diff.py"`:
   - Normal: `{base} {tmp_dir}/diff.txt`
   - Range: `--range {from} {to} {tmp_dir}/diff.txt`
3. Spawn `scope_analysis_{timestamp}` with `templates/scope-analysis.md`, expected `template_id` `b3e2f1a7-9c84-4d56-8e3b-7f1a4c9d2e85`, and variables `plugin_root`, `tmp_dir`, and `user_requested`. Wait for `{line_count, scopes, extension_summary, rationale, template_id}`.
4. If `line_count` is zero, create the header from `templates/review-doc.md` at the final path, with no finding sections, then clean up and report zero findings.
5. For every `(scope, reviewer)` pair, create a unique task name such as `review_{scope_id}_{slug}` and spawn a reviewer with the selected reviewer template. Pass `plugin_root`, target description, base/range, diff path, scope paths, dedicated output path, document language, review mode, and `profile_path`. Queue work when the runtime has no free slot. Each output is `.codex/tmp/.../reviews/{scope_id}/review-{slug}.md`; expect `{path, critical, major, minor, info, template_id}`.
6. After all reviewers finish, spawn `review_aggregate_{timestamp}`. In addition to `templates/aggregator.md`, pass the bundled profile `../../references/agents/review-helper.md`, all reviewer output paths, reviewer names, final path, target description, round, mode, and language. Expected `template_id`: `7a5f8c1d-3e92-4b67-9c4a-2d8e1f7b3c54`.
7. Confirm the final document exists. Remove only the run directory with `python "{plugin_root}/scripts/del_tmp.py" {tmp_dir}`.

Use `reviewer.md` template ID `4d8c2e5b-1f73-4a96-b2e8-9c1d3a7f4b62`; adversarial template ID `2e68714d-36e4-4a4c-a557-d34a81661cb1`. Retry a template-ID mismatch once as required by the shared contract.

Report the final document path, total findings, severity counts, reviewers used, and duplicates merged.

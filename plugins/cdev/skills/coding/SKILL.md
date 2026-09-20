---
name: coding
description: Run an explicitly requested multi-agent coding workflow with a persistent producer and reviewer through design, implementation, review, and QA. Use only when the user asks for CDev, multiple agents, delegation, or a team workflow; do not activate for an ordinary coding request.
---

# Multi-Agent Coding

Act as the root team leader. Orchestrate the work and enforce gates; do not design, implement, or review code yourself.

This skill requires `spawn_agent`, `followup_task`, `wait_agent`, and agent-status inspection. Stop if collaboration is unavailable. The user must have explicitly authorized multi-agent work by invoking this skill or requesting delegation.

## Runtime and trust

Resolve `skill_dir` from this loaded file and `plugin_root` two levels above it. Use absolute paths in child tasks. Read `../../rules/teammate.md`.

The QA agent executes commands declared by the destination repository. Run this workflow only in a trusted repository. Do not broaden network, credential, deployment, or release authority.

Options:

- `--review-rounds N` — Producer/reviewer loop cap, default 5, range 1–10.
- `--qa-attempts N` — QA/fix loop cap, default 5, range 1–10.
- `--commit` — After QA passes, stage only this run's source paths and create one concise commit.
- `--output {dir}` — Directory for design documents retained after the run.

Fix `{timestamp}` once and set the working directory `{tmp_dir}` to `.codex/tmp/cdev-coding-{timestamp}/`. Set `{design_dir}` to `--output` when supplied, otherwise `.codex/tmp/cdev-coding-{timestamp}-design/`. Resolve relative paths from the destination repository root. Use a dedicated design directory; reject the repository root, directories containing source files, and `{tmp_dir}` itself or its descendants.

Before starting, check `git status --porcelain -uall`, excluding entries under `.codex/tmp/` and the explicitly supplied `--output` destination. If any staged, unstaged, or untracked changes remain, stop and ask the user to commit, stash, or choose another workflow.

Write design and finding prose in the user's language; keep field names and severity labels in English.

## Standing team

Use two persistent children plus the root leader:

- `cdev_reviewer_{timestamp}` — scopes the work, reviews design and code, performs comment review and QA.
- `cdev_producer_{timestamp}` — designs, implements, and applies review or QA fixes.

Spawn each task name once. A completed child is idle but retains context. Start its next turn with `collaboration.followup_task`; use `send_message` only to supplement a child that is currently running. Wait for each required result with `wait_agent`. Keep the runtime's spare slot available for a narrowly scoped temporary specialist if a concrete failure justifies it.

## Workflow

1. Create `{design_dir}`, `{tmp_dir}/reviews`, and `{tmp_dir}/qa`.
2. Spawn the reviewer with `templates/team-analysis.md`, expected ID `d8760930-8d32-42c1-b033-d61f0cbd19c7`, and variables `plugin_root`, task, output path `{tmp_dir}/team.jsonl`, and document language. It applies `../../rules/agents-detection.md`, writes a self-contained task summary plus producer/reviewer profile choices, and returns counts/path only.
3. Read `team.jsonl`. Spawn the producer with `templates/design.md`, expected ID `740fa1cf-fa38-40a0-85d0-4c9a99eab5de`, the task summary, assigned scope, output path `{design_dir}/design.md`, no feedback, and the selected producer profile. Use this design path for subsequent design review, revisions, and coding.
4. Send the idle reviewer a `followup_task` using `templates/design-review.md`, expected ID `448ee08a-0284-4066-9de9-9f82e9078914`, design path, task, and output `{tmp_dir}/reviews/design-{round}.jsonl`. On actionable findings, follow up the producer with the design template plus that findings path, then re-review. Stop after `--review-rounds`; unresolved Critical findings block coding, while unresolved Major findings are recorded in the final report.
5. Record the pre-coding tree with `python "{plugin_root}/scripts/fetch_diff.py" snapshot {tmp_dir}/baseline-tree`.
6. Follow up the producer with `templates/code.md`, expected ID `278bf9bd-53e2-4695-ad40-3fb91374519a`, the approved design, implementation scope, test-suite flag, and no feedback. It returns changed paths and a short summary.
7. Follow up the reviewer with `templates/comment-review.md`, expected ID `8004286a-f4b2-4a6a-a3cb-9adc9ea370f2`, the changed paths and design. It may edit comments only.
8. Follow up the reviewer with `templates/code-review.md`, expected ID `4abf814d-2e3e-4bec-8ff8-45c9a176b01f`, changed paths, design, and output `{tmp_dir}/reviews/code-{round}.jsonl`. On actionable findings, follow up the producer with the code template and findings path, then repeat comment and code review. At the cap, unresolved Critical findings block QA; unresolved Major findings remain visible.
9. Run QA up to `--qa-attempts`:
   - Capture this run's diff with `python "{plugin_root}/scripts/fetch_diff.py" diff {tmp_dir}/baseline-tree {tmp_dir}/changes.txt`.
   - Follow up the reviewer with `templates/qa.md`, bundled profile `../../references/agents/dev-helper.md`, expected ID `6a711cba-0da8-4177-a41f-ddb4cf2a6e1f`, temp path, diff path, and attempt number.
   - On failure, follow up the producer with the code template, `qa-result.jsonl`, and `build.log`; then repeat comment review, code review, and QA.
10. If QA passes and `--commit` is set, exclude `.codex/tmp/` and `{design_dir}` from the changed paths returned by the producer and formatter, then stage and commit only the remaining paths in one commit. Keep already-staged excluded paths out of the commit without altering their staged state. Skip the commit if no eligible paths remain. Never use `git add -A`.
11. Retain the final QA summary and review counts, then remove only `{tmp_dir}` with `python "{plugin_root}/scripts/del_tmp.py" "{tmp_dir}"`. Keep `{design_dir}` and its design documents.

Report design document paths, team task names, design/code review rounds, changed files, unresolved findings, QA result and warning, commit hash when applicable, and any failure that stopped a gate.

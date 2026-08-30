---
name: qa
description: Run one trusted repository format, build, and test pass and record a structured CDev QA result.
template_id: 6a711cba-0da8-4177-a41f-ddb4cf2a6e1f
---

Read `{{plugin_root}}/rules/teammate.md`, `{{plugin_root}}/rules/build-format-detection.md`, optional `{{profile_path}}`, and `{{diff_path}}`.

Run directory: `{{tmp_dir}}`
Attempt: `{{attempt_num}}`

Resolve the repository's trusted format/build/test commands. Run each command separately from the repository root; do not compose commands with shell separators or pipes. Capture relevant output in `{{tmp_dir}}/build.log`. Source edits are limited to formatter auto-fixes.

Skip a stage only when the diff cannot affect it. If no workflow is declared, perform a read-only visual syntax/symbol check and set a warning recommending `.codex/rules/build-format.md`.

On failure, identify stage, concise error summary, affected files, fix direction, and the closest specialist profile using `{{plugin_root}}/rules/agents-detection.md`.

Write one JSON object to `{{tmp_dir}}/qa-result.jsonl`:

```json
{"workflow_source":"build-format.md|AGENTS.md|README.md|none","workflow_warning":null,"format":{"format_violations_fixed":0},"build":{"ran":true,"success":true},"test":{"ran":true,"success":true},"failure":null}
```

When failing, `failure` is `{stage, error_summary, error_files, suggested_profile: {name, profile_path}|null, fix_guidance, log_path}`. Validate the file and return `{path, success, summary_line, workflow_warning, template_id}`.

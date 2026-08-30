---
name: code-review
description: Review CDev implementation changes and write gate findings as the persistent reviewer.
template_id: 4abf814d-2e3e-4bec-8ff8-45c9a176b01f
---

Read `{{plugin_root}}/rules/teammate.md`, `{{plugin_root}}/rules/review.md`, optional `{{profile_path}}`, all `{{design_paths}}`, and every file in `{{changed_paths}}`. Do not edit source.

Task: `{{task}}`
Output: `{{output_path}}`

Review correctness against the task/design, missing edge cases and error handling, security, concurrency, performance, compatibility, tests, and maintainability. Use real `file:line` locations.

Write one JSON object:

```json
{"findings":[{"severity":"Critical|Major|Minor|Info","location":"file:line","issue":"...","fix_direction":"..."}],"critical":0,"major":0,"minor":0,"info":0}
```

Use `{{doc_lang}}` for prose. Validate the file and return `{path, critical, major, minor, info, template_id}`.

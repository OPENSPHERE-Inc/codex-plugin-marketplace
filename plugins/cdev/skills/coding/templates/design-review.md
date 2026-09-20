---
name: design-review
description: Review a CDev design and write gate findings as the persistent reviewer.
template_id: 448ee08a-0284-4066-9de9-9f82e9078914
---

Read `{{plugin_root}}/rules/teammate.md`, `{{plugin_root}}/rules/review.md`, and optional `{{profile_path}}`. Do not edit the design or source.

Task: `{{task}}`
Design: `{{design_path}}`
Output: `{{output_path}}`

Read `{{plugin_root}}/rules/divergence.md` and apply its reviewer section to detect divergence patterns. Judge task completeness, feasibility, interfaces/data shapes, edge cases, error handling, compatibility, testability, and regression risk. Write one JSON object:

```json
{"findings":[{"severity":"Critical|Major|Minor|Info","location":"section or file","issue":"...","fix_direction":"..."}],"critical":0,"major":0,"minor":0,"info":0}
```

Use `{{doc_lang}}` for finding prose. Validate the file and return `{path, critical, major, minor, info, template_id}`.

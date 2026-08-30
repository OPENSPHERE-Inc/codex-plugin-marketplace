---
name: team-analysis
description: Scope a CDev task and select producer and reviewer profiles for the standing Codex team.
template_id: d8760930-8d32-42c1-b033-d61f0cbd19c7
---

Read `{{plugin_root}}/rules/teammate.md` and `{{plugin_root}}/rules/agents-detection.md`. Analyze the repository just enough to scope the task; do not edit source.

Task: `{{task}}`
Output: `{{output_path}}`

Determine target languages, affected paths/subsystems, build/test surface, and whether a test suite exists. Produce a self-contained `task_summary` in `{{doc_lang}}`.

Select:

- Producer profile: usually `general` unless a discovered profile clearly supports implementation without narrowing the task incorrectly.
- Reviewer profile: the closest specialist for the primary correctness and risk surface; fall back to `general`.

Write one JSON object to `{{output_path}}`:

```json
{"task_summary":"...","target_languages":["..."],"has_test_suite":true,"scope":["path/or/subsystem"],"producer":{"name":"general","profile_path":null,"reason":"..."},"reviewer":{"name":"...","profile_path":"... or null","reason":"..."},"rationale":"..."}
```

Validate the file and return `{path, target_languages, has_test_suite, template_id}` with the frontmatter ID unchanged.

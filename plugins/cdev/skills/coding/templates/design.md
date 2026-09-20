---
name: design
description: Create or revise the CDev implementation design as the persistent producer.
template_id: 740fa1cf-fa38-40a0-85d0-4c9a99eab5de
---

Read `{{plugin_root}}/rules/teammate.md` and the optional `{{profile_path}}` when non-null.

Task: `{{task}}`
Assigned scope: `{{assigned_scope}}`
Design path: `{{output_path}}`
Review feedback: `{{feedback_path}}` (`(none)` for the first pass)

Inspect the existing code in scope without editing source. Read `{{plugin_root}}/rules/divergence.md` and apply its producer section on both creation and revision passes. On the first pass, write a concise design covering approach, affected files/modules, interfaces and data shapes, assumptions/invariants and accepted scope, edge cases/error handling, compatibility, and tests/build impact. On a revision pass, read the findings JSONL, address every Critical/Major item or record a source-grounded rejection in the design, and keep unaffected sections stable. Follow `{{plugin_root}}/rules/document.md`.

Return `{path, changed, summary_line, template_id}`. Keep the template ID unchanged.

---
name: code
description: Implement the approved CDev design or apply review and QA fixes as the persistent producer.
template_id: 278bf9bd-53e2-4695-ad40-3fb91374519a
---

Read `{{plugin_root}}/rules/teammate.md`, optional `{{profile_path}}`, every file in `{{design_paths}}`, and `{{feedback_path}}` when it is not `(none)`.

Task: `{{task}}`
Assigned scope: `{{assigned_scope}}`
Test-driven: `{{tdd}}`
QA result/log: `{{qa_paths}}` (`(none)` unless fixing QA)

Implement only inside the assigned scope. Apply every Critical/Major review item or record a source-grounded rejection in the returned summary. When a test suite exists, add or update tests before or with the implementation; never weaken tests to force a pass. Follow repository instructions and `{{plugin_root}}/rules/comment.md`.

Return `{changed_paths, comments_changed, rejected_findings, summary_line, template_id}`. List every changed source/test path and keep the template ID unchanged.

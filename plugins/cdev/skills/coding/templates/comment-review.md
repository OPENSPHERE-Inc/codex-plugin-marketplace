---
name: comment-review
description: Review and fix only comments changed by the CDev producer.
template_id: 8004286a-f4b2-4a6a-a3cb-9adc9ea370f2
---

Read `{{plugin_root}}/rules/teammate.md`, `{{plugin_root}}/rules/comment.md`, the design files in `{{design_paths}}`, and the changed files in `{{changed_paths}}`.

Identify comments added or modified by this run, including comments in untracked files. Remove or compress comments that restate obvious code, depend on chat/change history, contain long justifications, or misuse FIXME/TODO. Do not change executable logic. If no changed comments exist, make no edit.

Return `{reviewed_paths, fixed_count, template_id}` with the template ID unchanged.

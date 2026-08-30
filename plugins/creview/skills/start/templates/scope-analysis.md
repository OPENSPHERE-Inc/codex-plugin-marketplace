---
name: scope-analysis
description: Split a review diff into bounded scopes and select relevant Codex specialist profiles.
template_id: b3e2f1a7-9c84-4d56-8e3b-7f1a4c9d2e85
---

Read `{{tmp_dir}}/diff.txt`, count changed lines, split the diff into review scopes, and select specialist perspectives. Read `{{plugin_root}}/rules/sub-agent.md` and `{{plugin_root}}/rules/agents-detection.md` first.

User-requested reviewers: `{{user_requested}}` (possibly empty).

## Scope construction

1. Determine changed paths, languages, subsystems, and risk areas. `line_count` is the total added and removed lines.
2. Keep one scope when there are at most 800 changed lines and 20 files.
3. Otherwise group by cohesion, then keep each scope at or below 400 changed lines and 10 files when possible. Never split a file. Cap at 8 scopes and explain any overflow.
4. Assign every changed file to exactly one scope and name scopes `s1`, `s2`, ... in stable path order.

## Reviewer selection

For each scope, apply the specialist-profile detection rule. Add each materially relevant profile as `{name, profile_path, reason}`. Use one `{name: "general", profile_path: null, reason: "no matching specialist profile"}` when none match. Add each user-requested reviewer to every scope unless already present; resolve its profile path when possible.

Return `{line_count, scopes: [{scope_id, paths, line_count, reviewers: [{name, profile_path, reason}]}], extension_summary, rationale, template_id}`. Return the frontmatter `template_id` unchanged.

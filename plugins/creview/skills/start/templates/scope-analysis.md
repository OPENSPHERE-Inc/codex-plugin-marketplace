---
name: scope-analysis
description: Split a review diff into bounded scopes and select relevant Codex specialist profiles.
template_id: b3e2f1a7-9c84-4d56-8e3b-7f1a4c9d2e85
---

Read `{{tmp_dir}}/diff.txt`, count changed lines and files, split the diff into review scopes, and select specialist perspectives. Read `{{plugin_root}}/rules/sub-agent.md` and `{{plugin_root}}/rules/agents-detection.md` first.

User-requested reviewers: `{{user_requested}}` (possibly empty).

## Scope construction

1. Determine changed paths, languages, subsystems, and risk areas. `line_count` is the total added and removed lines. `file_count` counts changed files, including binaries, mode changes, empty additions/deletions, and renames without changed lines. Count a path appearing in several sections once. Return empty `scopes` when zero.
2. Keep one scope when there are at most 800 changed lines and 20 files.
3. Otherwise group by cohesion, then keep each scope at or below 400 changed lines and 10 files when possible. Never split a file. Cap at 8 scopes and explain any overflow.
4. Assign every changed file to exactly one scope and name scopes `s1`, `s2`, ... in stable path order.

## Reviewer selection

For each scope, apply the specialist-profile detection rule. Add each materially relevant profile as `{name, profile_path, reason}`. Use one `{name: "general", profile_path: null, reason: "no matching specialist profile"}` when none match. Add each user-requested reviewer to every scope unless already present; resolve its profile path when possible.

If all selected profiles cover narrower concerns than the changed code's behavior (for example, comments only), add one `general` reviewer with no profile path. Do not duplicate an existing general reviewer.

Include files without changed lines in the file-count bounds. Select reviewers for images and similar files from their uses in source as well as their extensions; a web image can require layout or rendering review. Exclude bundled `review-helper` and `pr-description-reviewer` from automatic selection because they have fixed roles.

Return `{line_count, file_count, scopes: [{scope_id, paths, line_count, reviewers: [{name, profile_path, reason}]}], extension_summary, rationale, template_id}`. Return the frontmatter `template_id` unchanged.

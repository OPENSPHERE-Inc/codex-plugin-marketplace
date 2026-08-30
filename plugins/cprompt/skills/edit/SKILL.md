---
name: edit
description: Create or revise AI-facing Markdown prompts, Codex SKILL.md files, AGENTS.md instructions, and sub-agent task templates. Use when prompt wording or skill instructions are the deliverable; do not use for ordinary human-facing documentation.
---

# Prompt Editor

Produce a concise AI-facing prompt that preserves the requested behavior after compression.

Resolve all supporting paths relative to this `SKILL.md` file:

- Prompt discipline: `../../rules/prompt.md`
- Human-document boundary: `../../rules/document.md`
- Starters: `templates/{kind}.md`

## Input

The request supplies an existing target path plus edit requirements, or a kind, target path, and requirements for a new file. Infer the kind when it is omitted:

- A path ending in `SKILL.md` → `skill`
- `AGENTS.md` or another instruction/rule Markdown file → `rule`
- A reusable role prompt for a spawned agent → `agent`
- Any other AI-facing Markdown → `prompt`

Codex skills replace Claude-style slash-command files. When asked to create or migrate a command, create a `skill` and explain the mapping in the final report.

## Output constraints

- Keep the target in the language requested by the user or already used by the file.
- Preserve machine-readable frontmatter, placeholders, JSON field names, tool names, and code identifiers unless the request changes them.
- Do not add unsupported Codex skill frontmatter. A skill requires `name` and `description`; keep supported existing fields only.
- Externalize a Markdown output skeleton to `templates/{name}.md` when embedding it would create Markdown-inside-Markdown ambiguity. Reference the external template from the prompt.
- Inside a fenced sub-agent task prompt, use plain prose and lists; avoid decorative headings and emphasis unless they are part of the output being specified.

## Workflow

1. Read `../../rules/prompt.md`. If the target is human-facing documentation, stop and report that this skill is out of scope; use the document rules instead.
2. For a new file, read the matching starter under `templates/`, adapt it to the requirements, and create the target directory when needed. For an edit, read the target and make the requested change.
3. Audit the result against every applicable prompt-discipline rule. Record violations as `path:line`, fix them, and repeat once. If a real ambiguity remains, present it to the user instead of inventing intent.
4. Compress the result. Remove politeness, repetition, self-evident instructions, effect-restating explanations, and examples that do not change behavior. Retain decision criteria, safety boundaries, authorization requirements, fallbacks, and input/output contracts.
5. Build an interpretation checklist covering inputs, branch conditions, failure paths, side effects, and output. Reread only the produced prompt and answer the checklist from its text. Fix any unclear item and repeat, up to three passes.
6. Validate a created or substantially changed Codex skill with the available `quick_validate.py` from `skill-creator`. If it is unavailable, verify the YAML frontmatter, folder/name match, and absence of unfinished placeholders manually.

Do not spawn a test agent unless the user explicitly requested delegation or an independent agent evaluation. When such delegation is authorized and available, give the evaluator the target prompt and checklist but not the intended answers.

## Report

Report the target path, violations fixed, whether compression changed the file, validation performed, and any unresolved checklist items.

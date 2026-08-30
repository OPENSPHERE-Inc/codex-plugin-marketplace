# cprompt

*[日本語版 README](README_ja.md)*

`cprompt` creates or revises instructions intended for another AI agent. It
loads the relevant prompt rules, chooses a matching template, edits the target,
and performs a concise self-review.

## Invocation

~~~text
$cprompt:edit Create a repository skill for release-note generation.
$cprompt:edit Improve AGENTS.md so that test requirements are unambiguous.
~~~

The skill supports:

- Codex skills
- repository instructions such as `AGENTS.md`
- agent role and task prompts
- reusable prompt templates

Claude Code command files are not a Codex primitive. When a migrated prompt was
formerly a command, `cprompt` converts it into a skill or a reusable task
template according to its purpose.

## Workflow

1. Identify the prompt type, audience, target path, and constraints.
2. Read the nearest repository instructions before editing.
3. Apply the matching template and prompt-design rules.
4. Check scope, activation wording, tool assumptions, placeholders, and output
   contract.
5. Report the changed file and any unresolved assumptions.

`cprompt` does not delegate work unless the user explicitly requests
multi-agent execution.

## Files

- `skills/edit/SKILL.md`: workflow entry point
- `skills/edit/templates/`: prompt-type templates
- `rules/prompt.md`: prompt design requirements
- `rules/document.md`: Markdown conventions

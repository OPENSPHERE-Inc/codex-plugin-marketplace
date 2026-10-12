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

## Worktree execution

`$cprompt:edit --worktree[=branch]` creates a separate checkout under
`.codex/worktrees/` and enables `--commit`. An existing branch starts at its tip; a missing
branch starts at the current HEAD. Without a branch name, it creates
`cprompt-edit-{timestamp}`. A branch already checked out elsewhere is rejected.
The invocation checkout may contain uncommitted changes; those changes are not copied.

Relative source paths resolve against the worktree. Absolute paths into the original checkout
are read-only references and are not rewritten. Documents and scratch files stay in the invocation
checkout; relative output destinations resolve there too. Retained documents cannot be placed
inside the worktree. Project Codex profiles and `.codex/rules/` are read from the invocation
checkout.

At completion the worktree is removed and the branch is retained. If uncommitted changes or
another condition prevent removal, the worktree is kept and its path is reported. Removal also
deletes ignored files inside it. The workflow does not merge or push the branch.

`--commit` also works on its own. It commits only this run's validated edits and stops before
editing if the target has uncommitted changes. Worktree mode requires a repository-relative,
non-ignored target without `..`, and invocation from the repository root. Absolute targets are
rejected in that mode. If an existing target is absent from the selected branch, the run stops.
If any edited or created file is ignored by Git and cannot be committed, its worktree is retained.

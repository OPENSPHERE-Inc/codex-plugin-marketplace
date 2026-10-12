# AGENTS.md

## Repository purpose

This repository distributes the `cprompt`, `creview`, and `cdev` Codex
plugins through `.agents/plugins/marketplace.json`.

## Codex Instructions

Before starting each type of work below, read and follow the linked instructions.
These files are not loaded automatically. Resolve the links relative to this
AGENTS.md and apply all instruction files relevant to the task.

- [Development](.codex/instructions/development.md): code changes, tests,
  completion checks, and formatting.
- [Comments](.codex/instructions/comment.md): code comments and deferred fixes.
- [Prompts](.codex/instructions/prompt.md): AI-facing skills, templates, rules,
  agent definitions, and AGENTS.md.
- [Documentation](.codex/instructions/document.md): human-facing README files,
  API references, and design documents.
- [Review](.codex/instructions/review.md): code review findings and severity.
- [Commits](.codex/instructions/commit.md): commit messages and trailers.

## Source and distribution policy

- `src/<plugin>/` is the Japanese source of truth.
- `plugins/<plugin>/` is the active English distribution.
- Change the Japanese source first, then apply an equivalent English
  translation to the active tree.
- Keep both runtime trees structurally identical.
- `.codex-plugin/plugin.json` and bilingual README files are distribution
  metadata and exist only in the active plugin tree.

## Implementation rules

- Use Codex plugin, skill, and collaboration concepts. Do not introduce Claude
  Code commands, hooks, tool declarations, or plugin-root variables.
- Multi-agent workflows must require explicit invocation.
- Respect the current collaboration slot limit. Queue work instead of assuming
  unlimited agents.
- Keep scripts compatible with Python 3.11 or later and Windows, macOS, and
  Linux.
- Write workflow scratch data only below `.codex/tmp/` in the invocation checkout.
  Worktree runs edit sources under `.codex/worktrees/` and keep documents and
  scratch data in the invocation checkout; pass absolute `target_dir` and
  `main_root` to all child tasks and use explicit command working directories.
- Keep `scripts/worktree.py` identical across all three plugins and both trees,
  and `scripts/lib/scratch_guard.py` identical across creview/cdev and both trees.
- Preserve the `template_id` line in task templates and keep each ID unique
  within a plugin.

## Validation

Run both commands after changing runtime content:

~~~console
python scripts/validate_repository.py
python -m unittest discover -s tests -v
~~~

Validate each plugin manifest with the Codex plugin validator when it is
available in the development environment.

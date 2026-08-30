# AGENTS.md

## Repository purpose

This repository distributes the `cprompt`, `creview`, and `cdev` Codex
plugins through `.agents/plugins/marketplace.json`.

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
- Write workflow scratch data only below the destination repository's
  `.codex/tmp/` directory.
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

# OPENSPHERE Codex Plugin Marketplace

*[日本語版 README](README_ja.md)*

A Codex plugin marketplace maintained by OPENSPHERE Inc. It ports the
`cprompt`, `creview`, and `cdev` workflows from
`claude-plugin-marketplace` to Codex-native skills and collaboration tools.

## Plugins

| Plugin | Skill | Purpose |
| --- | --- | --- |
| `cprompt` | `$cprompt:edit` | Create or revise AI-facing prompts and self-review them. |
| `creview` | `$creview:start`, `$creview:triage`, `$creview:respond`, `$creview:resolve`, `$creview:rounds` | Run a staged multi-agent code review. |
| `cdev` | `$cdev:coding` | Implement a coding task with persistent producer and reviewer agents. |

The multi-agent skills activate only when explicitly invoked. Ordinary review
and coding requests do not implicitly start these workflows.

## Installation

Add a local checkout as a marketplace:

~~~console
codex plugin marketplace add .
codex plugin add cprompt@opensphere-inc-codex
codex plugin add creview@opensphere-inc-codex
codex plugin add cdev@opensphere-inc-codex
~~~

Codex can also add the GitHub repository directly:

~~~console
codex plugin marketplace add OPENSPHERE-Inc/codex-plugin-marketplace
~~~

After installing or updating a plugin, start a new Codex conversation so that
its skills are reloaded.

## Repository layout

~~~text
.agents/plugins/marketplace.json  Marketplace catalog
plugins/<name>/                   Active English plugin
src/<name>/                       Japanese source of truth
scripts/validate_repository.py    Repository validation
tests/                            Helper-script integration tests
~~~

The runtime trees under `plugins/<name>/` and `src/<name>/` must have the
same relative file set. Edit the Japanese source first, then translate the same
change into the English active tree. Manifests and bilingual README files are
distribution metadata and therefore live only under `plugins/`.

## Development

Requirements:

- Codex CLI with plugin support
- Python 3.11 or later
- Git
- Codex collaboration tools for `creview` and `cdev`

Run the repository checks before publishing:

~~~console
python scripts/validate_repository.py
python -m unittest discover -s tests -v
~~~

The plugins write temporary workflow artifacts below the destination
repository's `.codex/tmp/` directory. Review documents are written below
`.codex/reviews/`.

## License

MIT. See [LICENSE](LICENSE).

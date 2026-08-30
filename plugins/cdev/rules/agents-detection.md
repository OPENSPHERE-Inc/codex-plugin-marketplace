# Specialist Profile Detection

Codex collaboration agents are spawned by task name. Use discovered agent configuration as prompt context, not as a runtime type selector.

Inspect these scopes in priority order:

1. Project `.codex/config.toml` `[agents.*]` entries and `.codex/agents/**/*.toml`.
2. `${CODEX_HOME}/config.toml` and `${CODEX_HOME}/agents/**/*.toml`; default `CODEX_HOME` to `~/.codex`.
3. `{{plugin_root}}/references/agents/**/*.md`.

Collect `{name, description, profile_path, config_file}` where available; higher-priority entries win name collisions. Match descriptions to the requested role, language, subsystem, and risk. Return the closest profile or `{name: "general", profile_path: null}`. A child reads the profile and any referenced config file for perspective but remains bounded by its task template.

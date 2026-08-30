# Specialist Profile Detection

Use this procedure when a creview template needs one specialist perspective. Codex collaboration agents are spawned by task name; a discovered profile is prompt context, not a `subagent_type` selector.

## Enumeration

Inspect these scopes in priority order and skip missing locations:

1. Project: `.codex/config.toml` entries under `[agents.*]`, then `.codex/agents/**/*.toml`.
2. User: `${CODEX_HOME}/config.toml` and `${CODEX_HOME}/agents/**/*.toml`; when `CODEX_HOME` is unset, use `~/.codex`.
3. Plugin bundle: `{{plugin_root}}/references/agents/**/*.md`.

For config entries, collect the agent name, description, and referenced `config_file` when present. For a TOML or Markdown profile, collect its path and description. A higher-priority scope wins when names collide.

## Selection

Compare each description with the caller's match target: affected language, subsystem, risk, finding content, or verification failure. Select the single closest match. If no profile is materially relevant, return `general` with no profile path.

## Result

Return or store `{name, profile_path, reason}` in the field requested by the caller. Before acting, the spawned child reads `profile_path` when non-null and any `config_file` it names. The child treats that content as a specialist perspective while continuing to obey the launch template and authorization boundary.

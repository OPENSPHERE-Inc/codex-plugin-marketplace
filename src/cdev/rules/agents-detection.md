# specialist profile検出

Codex collaboration agentはtask nameでspawnされる。検出したagent設定はprompt contextとして使い、runtime type selectorには使わない。

次のscopeを優先順に調べる:

1. プロジェクトの`.codex/config.toml`にある`[agents.*]`と`.codex/agents/**/*.toml`。
2. `${CODEX_HOME}/config.toml`と`${CODEX_HOME}/agents/**/*.toml`。`CODEX_HOME`のデフォルトは`~/.codex`。
3. `{{plugin_root}}/references/agents/**/*.md`。

利用可能な`{name, description, profile_path, config_file}`を収集し、同名衝突は上位scopeを優先する。要求role、言語、subsystem、riskへ最も近いprofileを返す。該当が無ければ`{name: "general", profile_path: null}`を使う。childはprofileと参照先config fileを専門視点として読み、task templateの境界には従い続ける。

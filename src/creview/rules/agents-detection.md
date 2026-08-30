# specialist profile 検出

creview テンプレートが 1 つの専門視点を必要とするとき、この手順を使う。Codex collaboration agent は task name で spawn されるため、検出した profile はプロンプト文脈であり `subagent_type` セレクターではない。

## 列挙

次のスコープを優先順に調べ、存在しない場所は飛ばす:

1. プロジェクト: `.codex/config.toml` の `[agents.*]` エントリ、その後 `.codex/agents/**/*.toml`。
2. ユーザー: `${CODEX_HOME}/config.toml` と `${CODEX_HOME}/agents/**/*.toml`。`CODEX_HOME` が未設定なら `~/.codex` を使う。
3. プラグイン同梱: `{{plugin_root}}/references/agents/**/*.md`。

config エントリでは agent name、description、存在する場合は参照先 `config_file` を収集する。TOML または Markdown profile ではパスと description を収集する。同名が衝突した場合は優先度の高いスコープを採用する。

## 選定

各 description と、呼び出し元が渡した照合対象（対象言語、subsystem、risk、finding 内容、verification failure）を比較する。最も近いものを 1 つ選ぶ。実質的に該当する profile が無い場合は profile path なしの `general` を返す。

## 結果

呼び出し元が指定したフィールドへ `{name, profile_path, reason}` を返すか保存する。spawn された子は行動前に、null でない `profile_path` と、そこに指定された `config_file` を読む。その内容を専門視点として扱い、起動テンプレートと権限境界には引き続き従う。

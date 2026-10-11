# OPENSPHERE Codex Plugin Marketplace

*[English README](README.md)*

OPENSPHERE Inc. が管理する Codex プラグインマーケットプレイスです。
`claude-plugin-marketplace` の `cprompt`、`creview`、`cdev` を、
Codex のスキルとコラボレーションツール向けに移植しています。

## プラグイン

| プラグイン | スキル | 用途 |
| --- | --- | --- |
| `cprompt` | `$cprompt:edit` | AI 向けプロンプトを作成・改訂し、自己レビューします。 |
| `creview` | `$creview:start`、`$creview:triage`、`$creview:respond`、`$creview:resolve`、`$creview:rounds` | 段階的なマルチエージェントコードレビューを実行します。 |
| `cdev` | `$cdev:coding` | producer と reviewer を維持しながらコーディングタスクを実装します。 |

マルチエージェントスキルは明示的に呼び出した場合だけ起動します。
通常のレビューや実装依頼から暗黙には起動しません。

## インストール

ローカルのチェックアウトをマーケットプレイスとして追加します。

~~~console
codex plugin marketplace add .
codex plugin add cprompt@opensphere-inc
codex plugin add creview@opensphere-inc
codex plugin add cdev@opensphere-inc
~~~

GitHub リポジトリも直接追加できます。

~~~console
codex plugin marketplace add OPENSPHERE-Inc/codex-plugin-marketplace
~~~

プラグインのインストールまたは更新後は、スキルを再読み込みするため
Codex で新しい会話を開始してください。

## リポジトリ構成

~~~text
.agents/plugins/marketplace.json  マーケットプレイスカタログ
plugins/<name>/                   英語のアクティブ版
src/<name>/                       日本語の正本
scripts/validate_repository.py    リポジトリ検証
tests/                            補助スクリプトの結合テスト
~~~

`plugins/<name>/` と `src/<name>/` のランタイムツリーは、同じ相対ファイル
構成を保ちます。まず日本語ソースを編集し、同じ変更を英語へ翻訳して
アクティブ版へ反映してください。manifest と日英 README は配布メタデータ
なので `plugins/` 側だけに配置します。

## 開発

必要な環境:

- プラグイン対応の Codex CLI
- Python 3.11 以降
- Git
- `creview` と `cdev` では Codex のコラボレーションツール

公開前に次の検証を実行します。

~~~console
python scripts/validate_repository.py
python -m unittest discover -s tests -v
~~~

一時ファイルと既定のレビュー・設計文書は対象リポジトリの `.codex/tmp/` 以下へ出力します。
`$cprompt:edit`、`$creview:rounds`、`$cdev:coding` は `--worktree[=branch]` で
`.codex/worktrees/` 内の別チェックアウトを使えます。この場合も文書と一時ファイルは
起動元に残り、検証後の変更は専用ブランチへコミットされます。
各プラグインの README にオプション、検証失敗時の扱い、出力先を記載しています。

## ライセンス

MIT。詳細は [LICENSE](LICENSE) を参照してください。

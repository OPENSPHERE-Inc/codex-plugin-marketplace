# cprompt

*[English README](README.md)*

`cprompt` は別の AI エージェントが読む指示を作成または改訂します。
関連ルールを読み、用途に合うテンプレートを選び、対象を編集した後に
簡潔な自己レビューを行います。

## 呼び出し例

~~~text
$cprompt:edit リリースノート生成用のリポジトリスキルを作成してください。
$cprompt:edit テスト要件が曖昧にならないよう AGENTS.md を改善してください。
~~~

次のプロンプト形式を扱います。

- Codex スキル
- `AGENTS.md` などのリポジトリ指示
- エージェントの役割・タスクプロンプト
- 再利用可能なプロンプトテンプレート

Claude Code の command ファイルは Codex のプリミティブではありません。
移植対象が command だった場合は、目的に応じてスキルまたは再利用可能な
タスクテンプレートへ変換します。

## ワークフロー

1. プロンプト種別、読者、対象パス、制約を特定します。
2. 編集前に最寄りのリポジトリ指示を読みます。
3. 対応するテンプレートとプロンプト設計ルールを適用します。
4. スコープ、起動条件、ツール前提、プレースホルダー、出力契約を確認します。
5. 変更ファイルと未解決の前提を報告します。

ユーザーが明示的にマルチエージェント実行を依頼しない限り、
`cprompt` は作業を委譲しません。

## ファイル

- `skills/edit/SKILL.md`: ワークフローのエントリーポイント
- `skills/edit/templates/`: プロンプト種別ごとのテンプレート
- `rules/prompt.md`: プロンプト設計要件
- `rules/document.md`: Markdown 規約

## worktree での実行

`$cprompt:edit --worktree[=branch]` は `.codex/worktrees/` に別 checkout を作り、
`--commit` も有効にします。branch が既存ならその tip、未作成なら現在の HEAD から開始し、
省略時は `cprompt-edit-{timestamp}` を新規作成します。別 checkout で使用中の branch は
指定できません。起動元の作業ツリーは未 commit の変更があっても利用できますが、その変更は
worktree へコピーされません。

source の相対パスは worktree 基準です。起動元内の絶対パスは読み取り専用で、
自動的に worktree 内へ置き換えません。文書と一時ファイルは起動元へ保存し、
相対の出力先も起動元基準で解決します。worktree 内を永続文書の出力先には指定できません。
project の Codex profile と `.codex/rules/` も起動元から読みます。

終了時は worktree を削除して branch を残します。未 commit 変更や削除を妨げる状態があれば
worktree を保持し、そのパスを報告します。削除時は内部の ignored file も削除されます。
branch の merge や push は行いません。

`--commit` 単独でも利用できます。検証が成功した今回の編集だけをコミットし、target に
未コミット変更があれば編集前に停止します。worktree mode はリポジトリルートから起動し、
`..` を含まない、Git が無視しないリポジトリ相対 target を指定してください。絶対 target は
拒否します。選択 branch に既存の編集対象がなければ停止します。
今回作成・編集した file が Git に無視されコミットできない場合も、worktree を保持します。

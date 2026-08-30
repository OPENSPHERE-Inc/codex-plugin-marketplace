# サブエージェント契約

creview スキルが起動するすべてのサブエージェントに適用する。

## 権限とスコープ

- ユーザーが creview スキルを明示的に起動した場合、または並列・マルチエージェントレビューを明示的に依頼した場合だけ委譲する。
- 起動テンプレートが割り当てた出力パスだけへ書き込む。
- ソース編集は fix、build-fix、comment-review、formatter タスクだけに許可し、割り当てられた範囲に限定する。それ以外のレビュータスクは読み取り専用とする。
- サブエージェントが起動した子は、親の書き込み・副作用制約を継承する。
- build、test、formatter、network、commit その他の状態変更コマンドは、テンプレートとユーザー権限が許可する場合だけ実行する。

## one-shot 起動

- `collaboration.spawn_agent` に一意な小文字の `task_name`、完全な `message`、必要最小限の `fork_turns` を指定する。ユーザーのタスク文脈全体が必要な場合は `fork_turns="all"` を使う。
- runtime の同時実行上限を守る。上限を超える作業はキューに置き、実行中の子が完了してから起動する。
- `collaboration.wait_agent` で完了を待つ。子の最終回答は親へ自動的に届く。
- one-shot タスクに `collaboration.send_message` や `collaboration.followup_task` を使わない。再試行は新しい一意な task name で spawn する。
- ユーザーまたは適用されるリポジトリ指示が求めない限り、model や reasoning の上書きを指定しない。

## 起動メッセージ

次をすべて含める:

1. 外部テンプレートの絶対パスと、行動前に読む指示。
2. 絶対 `plugin_root` を含むテンプレートの全 `{{...}}` プレースホルダー値。
3. ラウンド固有 override。無い場合も `(none)` と明記する。
4. 期待する `template_id` と、その値を変更せず返す要件。
5. 任意の specialist profile path。指定時はタスクテンプレートの後に読み、割り当て範囲を拡張せず専門視点を適用する。

起動メッセージ内でテンプレート本文を引用・要約しない。返された `template_id` が一致しない場合は新しい task name で一度だけ再試行する。2 回目も不一致なら中断して報告する。

## ファイル出力

- ファイル書き込みには利用可能なリポジトリ編集ツールを使い、shell heredoc を組み立てない。
- 1 オブジェクトとして定義された `.jsonl` 出力は、1 行に JSON オブジェクトを正確に 1 個だけ置く。
- `python "{{plugin_root}}/scripts/check-jsonl.py" {path}` で JSONL を検証し、エラーを修正してから返す。
- テンプレートが要求するフィールド名、Markdown 構造アンカー、finding ID、severity label、絵文字を維持する。

## 共通規約

コード編集時はこのファイルと同じディレクトリの `comment.md`、人間向け文書編集時は `document.md` を読む。

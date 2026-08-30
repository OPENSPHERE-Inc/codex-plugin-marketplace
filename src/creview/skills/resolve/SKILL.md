---
name: resolve
description: CReview ドキュメントに記録された修正を現在の差分に対して検証し、Verified または Feedback metadata を永続化する。ユーザーが CReview resolve phase を明示的に起動したときに使う。
---

# レビュー解決確認

finding を検証する。この phase では新しい修正を実装しない。

## runtime path と入力

絶対 `skill_dir` と `plugin_root` を解決し、`../../rules/sub-agent.md` を読む。入力は CReview ドキュメントと任意の `--base {branch}`。省略時は存在する `main`、次に `master` を選ぶ。

`.codex/tmp/creview-resolve-{timestamp}/verifications/` を作る。

## ワークフロー

1. `python "{plugin_root}/scripts/fetch_diff.py" {base} {tmp_dir}/diff.txt` で現在のレビュー差分を取得する。
2. `templates/analyze.md`、同梱 profile `../../references/agents/review-helper.md`、期待 ID `5d9e2c8a-1f74-4b63-a9d8-3c5f7e1b9a42`、変数 `plugin_root` と `document_path` で `resolve_analysis_{timestamp}` を spawn する。`{total, by_assignee, template_id}` を待つ。
3. 各 assignee を profile に解決し、`templates/verify.md`、期待 ID `8a1f5c9b-2e73-4d64-9c1e-8b3d7f2a5e94` で verification agent を spawn する。割り当て ID、ドキュメント、temp path、diff path、profile を渡す。空き slot を超える分はキューに置く。各 agent は `verifications/{id}.jsonl` を書き、ID と outcome だけを返す。
4. `python "{skill_dir}/scripts/compile-review.py" {tmp_dir} {document_path}` を実行する。`resolve-summary.md` を生成し、`verification` metadata を反映して件数を返す。
5. compile 成功を確認し、短いサマリーを保持した後、`python "{plugin_root}/scripts/del_tmp.py" {tmp_dir}` で run directory を削除する。詳細サマリーはユーザー応答に必要な場合だけ読む。

`✅ Verified` と `💬 Feedback` の値を正確に維持する。resolved、feedback、unresolved 件数とドキュメントパスを報告する。

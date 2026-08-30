---
name: triage
description: 既存 CReview ドキュメントの指摘を敵対的にトリアージし、採用作業を見積もり、triage と estimate metadata を永続化する。ユーザーがこの CReview phase またはマルチエージェントトリアージを明示的に求めたときに使う。
---

# レビュートリアージと見積もり

レビュードキュメントを handoff 境界として扱う。この phase ではソースを修正しない。

## runtime path

読み込まれたファイルから `skill_dir` を解決し、その 2 階層上を `plugin_root` とする。子メッセージには絶対値を使う。`../../rules/sub-agent.md` を読む。この phase には collaboration tool が必要で、challenge agent を nested spawn する場合がある。委譲できなければ停止する。

## 入力とオプション

- 必須: CReview ドキュメントのパス。
- `--adr` — 永続的な設計判断について estimate agent が ADR を作成・更新することを許可する。
- 上位ワークフローは過去 round のドキュメントパスと phase override を渡せる。

`{timestamp}` を一度確定し、`.codex/tmp/creview-triage-{timestamp}/estimates/` を作る。

## ワークフロー

1. `templates/triage.md`、期待 `template_id` `1e9c4f7a-5b82-4d63-a1c8-3f7d2e9b4a15`、変数 `plugin_root`、`document_path`、`tmp_dir`、`previous_round_doc_paths` で `triage_primary_{timestamp}` を spawn する。template は propose、独立 challenge、majority-gated adjudication を実行して `triage.jsonl` を書く。`{path, will_fix_count, wontfix_count, flipped_count, by_stage, by_assignee, template_id}` を待つ。
2. `error` が返った場合は run directory を削除し、レビュードキュメントを変更せず停止する。
3. Will-Fix の各 `by_assignee` group について、`templates/estimate.md` と期待 ID `8b2d5f1c-7a93-4e64-b8d1-2c5e9a3f7b48` で estimate agent を spawn する。ID 群、ドキュメント、run directory、ADR flag、timestamp、group の specialist profile path を渡す。同時実行上限を守ってキューに置く。各 agent は `estimates/{id}.jsonl` を書き、item ID、verdict、ADR path だけを返す。
4. estimate がある場合は、`templates/estimate-summary.md`、同梱 profile `../../references/agents/review-helper.md`、期待 ID `5c1e9b7a-3d48-4a96-b8e2-7f3c5a1d4b29` で `estimate_summary_{timestamp}` を spawn する。
5. `python "{skill_dir}/scripts/compile-review.py" {tmp_dir} {document_path}` を実行する。`triage.jsonl` と estimate JSONL を `events.jsonl` へまとめ、renderer を起動し、`triage` と `estimate` metadata だけを永続化する。
6. compile 成功を確認し、サマリーと件数を保持して `python "{plugin_root}/scripts/del_tmp.py" {tmp_dir}` で run directory を削除する。

この phase では `status` や `verification` を追加しない。構造 label と絵文字を正確に維持する。件数、ドキュメントパス、ADR path、次の phase が `$creview:respond` であることを報告する。

---
name: respond
description: CReview triage が永続化した Maintain と Alternative の指摘を修正し、comment・build 検証を行い、fix status を永続化する。ユーザーが CReview respond phase を明示的に起動したときに使う。
---

# レビュー対応

判断はレビュードキュメントから読む。`$creview:triage` と一時ディレクトリを共有していると仮定しない。

## runtime path とオプション

他の CReview スキルと同様に絶対 `skill_dir` と `plugin_root` を解決し、`../../rules/sub-agent.md` を読む。

- 必須: レビュードキュメントのパス。
- `--adr` — fix agent が estimate metadata に記録された ADR を読むことを許可する。
- `--commit` — 検証後、この phase が記録したファイルだけを stage して簡潔な commit を 1 つ作る。この option なしに commit 権限を推定しない。

`.codex/tmp/creview-respond-{timestamp}/statuses/` を作る。

## ワークフロー

1. `templates/select-fix-targets.md`、期待 ID `7c3e9a1d-5b48-4f62-9a8c-2d6f1b3e7a95`、変数 `plugin_root`、`document_path`、`tmp_dir` で `select_fix_targets_{timestamp}` を spawn する。`targets.jsonl` を書き、`{fix_count, by_assignee}` を返す。
2. target が無ければソース変更 step を飛ばして compile へ進む。
3. `../../rules/agents-detection.md` で各 assignee を Codex specialist profile に解決する。各 group を `templates/fix.md`、期待 ID `2f8a1c5d-7b94-4e63-a1c8-5d3f9b2e7a14` で spawn する。ID、ドキュメント、temp path、ADR flag、timestamp、profile path を渡す。空き slot を超える分はキューに置く。agent は `statuses/{id}.jsonl` を書く。
4. `python "{plugin_root}/scripts/fetch_diff.py" HEAD {tmp_dir}/changes.txt` で現在の fix diff を取得する。`templates/comment-review.md`、同梱 profile `../../references/agents/comment-sensei.md`、期待 ID `4a8e2d6f-9b15-4c73-8a2d-7f1e5c9b3d68` で `comment_review_{timestamp}` を spawn する。
5. format/build/test 検証ループを最大 5 回実行する。`templates/format-build-verify.md`、同梱 profile `../../references/agents/review-helper.md`、期待 ID `9d3c5f8a-2b71-4e94-a8c5-1f7d3b9e2c46` で `format_build_{timestamp}_{attempt}` を spawn する。失敗時は `format-build-result.jsonl` の運用 failure field だけを読み、specialist profile を解決して `templates/build-fix.md`、期待 ID `6e2a9f5c-1d83-4b74-9c2e-5a8d3f1b7e29` で `build_fix_{timestamp}_{attempt}` を spawn する。次の検証前に diff を再取得する。
6. `--commit` 指定時は、この run の status file に列挙されたパスだけを stage し、review document と `.codex/tmp` を除外して commit を 1 つ作る。`git add -A` は使わない。
7. `python "{skill_dir}/scripts/compile-review.py" {tmp_dir} {document_path}` で `status` metadata を永続化する。成功を確認して `python "{plugin_root}/scripts/del_tmp.py" {tmp_dir}` で run directory を削除する。

fixed 件数、変更ファイル、検証結果、該当時の commit hash、workflow warning、ドキュメントパスを報告する。build failure を成功として表現しない。

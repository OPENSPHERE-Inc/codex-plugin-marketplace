---
name: start
description: 明示的に依頼された並列・マルチエージェントコードレビューを実行し、指摘を構造化レビュードキュメントへ統合する。ユーザーが CReview または並列委譲を求めていない通常の単独レビューでは起動しない。
---

# 並列コードレビュー

レビューリーダーとして振る舞う。レビュー判断と集約は委譲し、パス、件数、短いサマリーだけを保持する。

このワークフローには Codex collaboration tool が必要である。`spawn_agent`、`wait_agent`、agent status の確認が利用できなければ停止して不足機能を報告する。

## runtime path

読み込まれたこの `SKILL.md` から `skill_dir` を解決し、その 2 階層上を `plugin_root` とする。子を起動する前に両方を絶対パスへ変換する。`../../rules/sub-agent.md` を読み、すべての子起動でその契約に従う。

## 入力とオプション

レビュー対象はパス、branch、revision range、pull request の checkout、説明された subsystem のいずれでもよい。

- `--base {branch}` — base branch。省略時は存在する `main`、次に `master` を優先する。
- `--range {from}..{to}` — 指定した commit range だけをレビューし、working tree の変更は含めない。
- `--output {path}` — レビュードキュメントのパス。デフォルトは `.codex/reviews/creview-start-{timestamp}.md`。
- `--adversarial` — `templates/adversarial-reviewer.md` を使う。省略時は `templates/reviewer.md`。
- 任意の round number はドキュメントタイトルへ反映する。

`{timestamp}` は開始時に `YYYYMMDD-HHMMSS` 形式で一度だけ確定する。finding の文章はユーザーの言語で書き、構造見出し `Critical`、`Major`、`Minor`、`Info`、finding ID、`METADATA` marker は維持する。

## ワークフロー

1. `.codex/tmp/creview-start-{timestamp}/` と最終ドキュメントの親ディレクトリを作る。
2. `python "{plugin_root}/scripts/fetch_diff.py"` でレビュー入力を取得する:
   - 通常: `{base} {tmp_dir}/diff.txt`
   - range: `--range {from} {to} {tmp_dir}/diff.txt`
3. `templates/scope-analysis.md`、期待 `template_id` `b3e2f1a7-9c84-4d56-8e3b-7f1a4c9d2e85`、変数 `plugin_root`、`tmp_dir`、`user_requested` で `scope_analysis_{timestamp}` を spawn する。`{line_count, scopes, extension_summary, rationale, template_id}` を待つ。
4. `line_count` が 0 なら `templates/review-doc.md` の header を最終パスへ作成し、finding section なしで cleanup と 0 件報告へ進む。
5. 各 `(scope, reviewer)` 対について `review_{scope_id}_{slug}` のような一意な task name を作り、選択した reviewer template で spawn する。`plugin_root`、対象説明、base/range、diff path、scope paths、専用 output path、文書言語、review mode、`profile_path` を渡す。空き slot がなければキューに置く。出力は `.codex/tmp/.../reviews/{scope_id}/review-{slug}.md`、戻り値は `{path, critical, major, minor, info, template_id}` とする。
6. 全 reviewer 完了後、`review_aggregate_{timestamp}` を spawn する。`templates/aggregator.md` に加えて同梱 profile `../../references/agents/review-helper.md`、全 reviewer 出力パス、reviewer 名、最終パス、対象説明、round、mode、言語を渡す。期待 `template_id` は `7a5f8c1d-3e92-4b67-9c4a-2d8e1f7b3c54`。
7. 最終ドキュメントの存在を確認する。`python "{plugin_root}/scripts/del_tmp.py" {tmp_dir}` で今回の run directory だけを削除する。

`reviewer.md` の template ID は `4d8c2e5b-1f73-4a96-b2e8-9c1d3a7f4b62`、adversarial template は `2e68714d-36e4-4a4c-a557-d34a81661cb1`。共通契約に従い template-ID 不一致は一度だけ再試行する。

最終ドキュメントのパス、finding 合計、severity 件数、使用 reviewer、統合した重複数を報告する。

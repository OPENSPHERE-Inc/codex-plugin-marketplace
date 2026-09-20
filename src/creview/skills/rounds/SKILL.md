---
name: rounds
description: 明示的に依頼された上限付き CReview round を start、triage、respond、resolve の合成で実行し、権限内の追加コード変更が無くなるまで繰り返す。通常のレビュー依頼では起動しない。
---

# マルチラウンドレビュー

root agent で 4 つの CReview phase skill を調整する。phase-leader agent は作らない。各 phase が自分のサブエージェント委譲を管理する。

## runtime path

この skill の絶対 `skill_dir` と `plugin_root` を解決し、`../../rules/sub-agent.md` を読む。phase 実行前に sibling skill file を読む:

- `../start/SKILL.md`
- `../triage/SKILL.md`
- `../respond/SKILL.md`
- `../resolve/SKILL.md`

## 入力とオプション

任意の位置引数を出力ベースパスとして受け取る。省略時はプロジェクトルートの `.codex/tmp/` を使う。

オプション:

- `--confirm`（デフォルト OFF）— triage と estimate の永続化後、respond 前に見積サマリーを示してユーザーの続行指示を待つ。
- `--confirm-round`（デフォルト OFF）— 次 round を開始する前にユーザーの続行指示を待つ。
- `--commit`（デフォルト OFF）— respond へ渡す。
- `--incremental`（デフォルト OFF）— Round 2 以降は branch 全体ではなく、前 round 開始 revision から今 round 開始 revision までの commit range だけをレビューする。この option は `--commit` も有効にする。
- `--adr`（デフォルト OFF）— triage または respond が永続的な設計判断の ADR をレビュードキュメントの隣に新規作成することを許可する。レビュードキュメントが参照する既存 ADR は、この option に関係なく読み込み、修正時に更新する。
- `--max-rounds N` — デフォルト 10、範囲 1〜20。
- `--base {branch}` — review base。省略時は存在する `main`、次に `master` を使う。`--incremental` は Round 2 以降この値を revision range で置き換える。
- `--adversarial`（デフォルト OFF）— start へ渡す。
- `--output-dir {path}` — 以前の Codex 版との互換 option。branch directory の選択を行わず、指定 path を今回の run directory として使う。位置引数と同時に指定された場合は停止して競合を報告する。

## レビュードキュメント

`--output-dir` がない場合、開始時に `git branch --show-current` で現在の branch 名を得て、次の規則で run directory を一度だけ決める:

- 初回は `{base-path}/{branch-name}/` を使い、branch 名の `/` はディレクトリ階層として保つ。
- 同じ branch directory が存在する場合、branch 名の末尾へ `_1`、`_2`、... を付け、存在しない最小番号を使う。
- 例: `feat/add-replay` の初回は `{base-path}/feat/add-replay/`、再実行は `{base-path}/feat/add-replay_1/`。
- 各 round は `{run-dir}/review-round{N}.md`、最終レポートは `{run-dir}/final-report.md`。

発散調査レポートは `{run-dir}/divergence-round{N}.md`。レビュー文書と各レポートはユーザーの言語で書く。

## round ワークフロー

1. option、run directory、round counter `1`、`prev_round_rev = (該当なし)`、round 固有 override `(none)`、`divergence_count = 0`、`report_path = null` を初期化する。clean worktree は要求せず、無関係なユーザー変更を維持する。
2. 各 round の開始時に `git rev-parse HEAD` を `this_round_rev` として記録し、レビュー対象を決める:
   - `--incremental` が OFF、または Round 1: `--base` を使い、revision range は指定しない。後続 round も commit と working tree を含む branch 全体の差分を再レビューする。
   - `--incremental` が ON の Round 2 以降: `prev_round_rev..this_round_rev` を使う。両 revision が同じなら新しい commit がないため round loop を終了する。
3. 明示 output `{run-dir}/review-round{N}.md` と確定した base または range で `start` を実行する。
4. そのドキュメントに `triage` を実行し、それ以前の全 round document path を過去 round context として渡す。`error` があれば以降の phase を実行せず、手順 9 で結果を記録して最終レポートへ進む。
5. Round 2 以降で `will_fix_count >= 1` かつ `maintain_count + alternative_count >= 1` の場合、下記の発散ゲートを実行する。フィードバックループ内では実行しない。
6. 発散を検出した場合は `report_path` を読んで内容を提示する。`--confirm` 指定時かつ Maintain / Alternative target がある場合は triage の `summary` を示す。いずれかに該当すれば、該当する内容をまとめて提示してユーザーの続行指示を 1 回待つ。発散時の確認は `--confirm` の状態に依存しない。
   - ユーザーが停止を指示した場合、以降の phase を実行せず手順 9 で結果を記録し、次 round へ進まず最終レポートへ進む。
   - 続行とともに修正方針が指定された場合、その原文と参照用の `report_path`（レポートがなければ null）を今 round の `respond` override として保持する。続行だけの指示で推奨案の採用を推定しない。
7. Maintain または Alternative target がある場合は ADR と commit option、今 round の override を渡して `respond` を実行する。無ければ `respond` だけを飛ばす。どちらの場合も `resolve` へ進み、Won't Fix と Downgrade も検証する。
8. `resolve` を実行する。Feedback が残る場合は、そのドキュメントに triage、必要な場合だけ respond、resolve を最大 3 回繰り返す。各 `respond` にユーザーの修正方針と `report_path` を再送する。`--confirm` の確認と停止指示の扱いは手順 6 に従うが、発散による確認は繰り返さない。triage error または停止指示がなければ、各 attempt の `resolve` は必ず実行する。
9. finding、decision、fix、verification 件数、workflow warning、`this_round_rev`、feedback attempt を記録する。未実行 phase の件数は 0 とする。全 `respond` 戻り値の論理和を `code_changed` とし、一度も実行しなかった場合は false とする。
10. error やユーザーの停止指示がなく、`code_changed` が true かつ現在の round number が `--max-rounds` 未満の場合だけ次 round へ進む。`--confirm-round` 指定時は次 round の開始前にユーザーの続行指示を待つ。停止指示なら最終レポートへ進む。継続時は `prev_round_rev = this_round_rev` として round number を増やし、round 固有 override と発散結果をリセットする。`--commit` は通常 mode の継続条件ではない。

## 発散ゲート

triage の一時ディレクトリは phase 完了時に削除されるため、`.codex/tmp/creview-divergence-{timestamp}-round{N}/` を専用の `gate_tmp_dir` として作る。`timestamp` は run 開始時に一度確定する。中間結果の本文は root context に載せず、パス・件数・選定 profile だけを保持する。

1. `templates/divergence-check.md`、同梱 profile `../../references/agents/review-helper.md`、期待 ID `6570a998-e9f3-4421-af84-6911eebd7c07` で検出 agent を 1 つ spawn する。変数: `plugin_root`、`document_path`、`previous_round_doc_paths`、`output_path = {gate_tmp_dir}/divergence.jsonl`。戻り値は `{divergence_count, investigator, template_id}`。
2. `divergence_count >= 1` の場合、検出ファイルの存在を確認し、`templates/divergence-investigate.md`、選定された `investigator.profile_path`（null なら profile なしの general agent）、期待 ID `ad54f81e-81f1-43c0-acff-0941524b8a3e` で調査 agent を 1 つ spawn する。変数: `plugin_root`、`divergence_path = {gate_tmp_dir}/divergence.jsonl`、`document_path`、`previous_round_doc_paths`、`template_path = {skill_dir}/templates/divergence-report.md`、`report_path = {run-dir}/divergence-round{N}.md`、`language`。全発散を同じ agent が調査する。返された `report_path` の存在を確認する。
3. 検出・必要な調査が成功したら、`python "{plugin_root}/scripts/del_tmp.py" {gate_tmp_dir}` で専用一時ディレクトリだけを削除し、round の確認へ戻る。0 件なら調査も発散による確認も不要。出力欠落や agent failure は報告し、round 結果を記録して最終レポートへ進む。修正は実行しない。

両 agent の override は `(none)`。起動メッセージ・template ID 検証・同時実行上限は `sub-agent.md` に従う。

## 最終レポート

`templates/final-report-compile.md`、同梱 profile `../../references/agents/review-helper.md`、期待 ID `4f8a2d1c-9b35-4e67-a2c1-8b5d3f9e7a16`、全 round document path と統計、`templates/final-report.md`、最終パス `{run-dir}/final-report.md`、ユーザーの言語を渡して aggregator を 1 つ spawn する。返されたパスの存在を確認する。

最終パス、round 数、finding 合計、fixed/resolved/unresolved 件数、停止条件、workflow warning を報告する。

---
name: rounds
description: 明示的に依頼された上限付き CReview round を start、triage、respond、resolve の合成で実行し、権限内の追加コード変更が無くなるまで繰り返す。通常のレビュー依頼では起動しない。
---

# マルチラウンドレビュー

root agent で 4 つの CReview phase skill を調整する。phase-leader agent は作らない。各 phase が自分のサブエージェント委譲を管理する。

## runtime path

この skill の絶対ディレクトリと `plugin_root` を解決する。phase 実行前に sibling skill file を読む:

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
- `--max-rounds N` — デフォルト 5、範囲 1〜10。
- `--base {branch}` — review base。省略時は存在する `main`、次に `master` を使う。`--incremental` は Round 2 以降この値を revision range で置き換える。
- `--adversarial`（デフォルト OFF）— start へ渡す。
- `--output-dir {path}` — 以前の Codex 版との互換 option。branch directory の選択を行わず、指定 path を今回の run directory として使う。位置引数と同時に指定された場合は停止して競合を報告する。

## レビュードキュメント

`--output-dir` がない場合、開始時に `git branch --show-current` で現在の branch 名を得て、次の規則で run directory を一度だけ決める:

- 初回は `{base-path}/{branch-name}/` を使い、branch 名の `/` はディレクトリ階層として保つ。
- 同じ branch directory が存在する場合、branch 名の末尾へ `_1`、`_2`、... を付け、存在しない最小番号を使う。
- 例: `feat/add-replay` の初回は `{base-path}/feat/add-replay/`、再実行は `{base-path}/feat/add-replay_1/`。
- 各 round は `{run-dir}/review-round{N}.md`、最終レポートは `{run-dir}/final-report.md`。

レビュー文書と最終レポートはユーザーの言語で書く。

## round ワークフロー

1. option、run directory、round counter `1`、`prev_round_rev = (該当なし)` を初期化する。clean worktree は要求せず、無関係なユーザー変更を維持する。
2. 各 round の開始時に `git rev-parse HEAD` を `this_round_rev` として記録し、レビュー対象を決める:
   - `--incremental` が OFF、または Round 1: `--base` を使い、revision range は指定しない。後続 round も commit と working tree を含む branch 全体の差分を再レビューする。
   - `--incremental` が ON の Round 2 以降: `prev_round_rev..this_round_rev` を使う。両 revision が同じなら新しい commit がないため round loop を終了する。
3. 明示 output `{run-dir}/review-round{N}.md` と確定した base または range で `start` を実行する。
4. そのドキュメントに `triage` を実行し、それ以前の全 round document path を過去 round context として渡す。
5. `--confirm` 指定時かつ Maintain または Alternative target がある場合は estimate summary を示し、修正前にユーザーの続行指示を待つ。
6. Maintain または Alternative target がある場合は ADR と commit option を渡して `respond` を実行する。無ければ `respond` だけを飛ばす。Won't Fix と Downgrade も verification を受けるため、どちらの場合も次の `resolve` へ進む。
7. `resolve` を実行する。Feedback が残る場合は、そのドキュメントに triage、必要な場合だけ respond、resolve を最大 3 回繰り返す。各 attempt の `resolve` は必ず実行する。
8. finding、decision、fix、verification 件数、workflow warning、`this_round_rev`、feedback attempt を記録し、全 `respond` 戻り値の論理和を `code_changed` とする。`respond` を一度も実行しなかった場合は false とする。
9. `code_changed` が true かつ現在の round number が `--max-rounds` 未満の場合だけ次 round へ進む。`--confirm-round` 指定時は次 round の開始前にユーザーの続行指示を待つ。継続時は `prev_round_rev = this_round_rev` として round number を増やす。`--commit` は通常 mode の継続条件ではない。

## 最終レポート

`templates/final-report-compile.md`、同梱 profile `../../references/agents/review-helper.md`、期待 ID `4f8a2d1c-9b35-4e67-a2c1-8b5d3f9e7a16`、全 round document path と統計、`templates/final-report.md`、最終パス `{run-dir}/final-report.md`、ユーザーの言語を渡して aggregator を 1 つ spawn する。返されたパスの存在を確認する。

最終パス、round 数、finding 合計、fixed/resolved/unresolved 件数、停止条件、workflow warning を報告する。

---
name: rounds
description: 明示的に依頼された上限付き CReview round を start、triage、respond、resolve の合成で実行し、権限内の追加コード変更が無くなるまで繰り返す。通常のレビュー依頼では起動しない。
---

# マルチラウンドレビュー

root agent で 4 つの CReview phase skill を調整する。phase-leader agent は作らない。各 phase が自分のサブエージェント委譲を管理する。

## runtime path とオプション

この skill の絶対ディレクトリと `plugin_root` を解決する。phase 実行前に sibling skill file を読む:

- `../start/SKILL.md`
- `../triage/SKILL.md`
- `../respond/SKILL.md`
- `../resolve/SKILL.md`

オプション:

- `--max-rounds N` — デフォルト 2、範囲 1〜5。
- `--base {branch}` — review base。
- `--output-dir {path}` — デフォルト `.codex/reviews/creview-rounds-{branch}-{timestamp}`。
- `--adversarial`、`--adr` — 対応 phase へ渡す。
- `--commit` — respond へ渡す。後続 round に安定した revision 境界が必要なため、複数 review round には commit が必要。
- `--confirm` — triage 後、respond 前に一時停止する。
- `--confirm-round` — feedback または unresolved finding が残る状態で次 round へ進む前に一時停止する。

## round ワークフロー

1. 開始 revision を記録し、output directory を作る。レビューのために clean worktree を要求せず、無関係なユーザー変更を維持する。
2. 各 round で明示 output `round-{N}.md` を使って `start` ワークフローを実行する。Round 1 は要求された対象をレビューし、後続 round は前 round の commit revision から現在の `HEAD` をレビューする。
3. そのドキュメントに `triage` を実行し、それ以前の全 round document を過去 round context として渡す。
4. `--confirm` 指定時は estimate summary を示し、修正前にユーザーを待つ。
5. Maintain または Alternative target がある場合は、ADR と commit option を渡して `respond` を実行する。無ければ飛ばす。
6. `resolve` を実行する。Feedback が残る場合は、そのドキュメントに triage → respond → resolve を最大 3 回繰り返す。
7. finding、decision、fix、verification 件数、workflow warning、revision、feedback attempt を記録する。
8. round がコードを変更し、`--commit` により新しい `HEAD` が生まれ、round 上限内の場合だけ次 round を開始する。`--commit` なしでは現在 round で停止し、追加 round には安定した commit 境界が必要と報告する。

## 最終レポート

`templates/final-report-compile.md`、同梱 profile `../../references/agents/review-helper.md`、期待 ID `4f8a2d1c-9b35-4e67-a2c1-8b5d3f9e7a16`、全 round document path と統計、`templates/final-report.md`、最終パス `{output_dir}/final-report.md`、ユーザーの言語を渡して aggregator を 1 つ spawn する。返されたパスの存在を確認する。

最終パス、round 数、finding 合計、fixed/resolved/unresolved 件数、停止条件、workflow warning を報告する。

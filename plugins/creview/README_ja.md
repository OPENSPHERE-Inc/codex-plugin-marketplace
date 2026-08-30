# creview

*[English README](README.md)*

`creview` は明示的に呼び出す、Codex 向けの段階的なマルチエージェント
コードレビューワークフローです。Claude 固有のバックグラウンドタスクと
`agent-sequencer` を Codex のコラボレーション操作へ置き換えています。

## スキル

| スキル | 用途 |
| --- | --- |
| `$creview:start` | レビュアーを選び、対象スコープを並列レビューしてレビュー文書を作成します。 |
| `$creview:triage` | 指摘を反証・裁定し、分類と見積もりを行います。 |
| `$creview:respond` | 受け入れた修正を実装し、指摘ステータスを更新します。 |
| `$creview:resolve` | ソース上で修正を検証し、結果を記録します。 |
| `$creview:rounds` | 停止条件まで4段階を複数ラウンド実行します。 |

呼び出し例:

~~~text
$creview:rounds .codex/tmp --base origin/main --max-rounds 3
~~~

`$creview:rounds` は Claude 版と同じ入出力指定を受け付け、`.claude/` の代わりに
`.codex/` を使います。

- 任意の位置引数として出力ベースパスを指定でき、デフォルトは `.codex/tmp/` です。
- `--confirm`、`--confirm-round`、`--commit`、`--incremental`、`--adr`、
  `--adversarial` はすべてデフォルト OFF です。
- `--max-rounds N` はデフォルト 5、範囲 1〜10 です。
- `--base {branch}` は省略時に存在する `main`、次に `master` を使います。
- 以前の Codex 版が使っていた `--output-dir {path}` は、位置引数へ branch directory を
  加える代わりに、今回の run directory を直接指定します。

通常は working tree を含む branch 全体の差分を各ラウンドで再レビューするため、
commit は不要です。`--incremental` は直前ラウンドが追加した commit だけをレビューし、
同時に `--commit` も有効にします。

## 実行モデル

- ルートエージェントがワークフローリーダーを維持します。
- 独立したレビュアーを Codex のコラボレーションツールで起動します。
- 利用可能なスロット数を超える作業はキューに入れます。
- 1回限りのレビュアーは構造化 JSONL を返し、再利用しません。
- プロジェクトまたはユーザーの Codex エージェント設定からプロファイル情報を
  検出でき、同梱の参照プロファイルをフォールバックに利用します。

名前付き Claude サブエージェント型を仮定せず、外部 sequencer
プラグインも必要としません。

## 出力

デフォルトでは `$creview:start` が
`.codex/tmp/creview-start-{timestamp}.md` を作成します。`$creview:rounds` は
`.codex/tmp/{branch-path}/review-round{N}.md` と `final-report.md` を作成し、
同じ branch で再実行すると branch 名へ未使用の最小 `_N` suffix を付けます。
明示的な output path または rounds base path を指定すれば、別の場所へ保存できます。

一時プロンプト、JSONL 応答、差分データは `.codex/tmp/` 以下だけに置き、
補助スクリプトは一時領域外の一時パスを拒否します。

Python 補助スクリプトが差分取得、JSONL 検証、文書レンダリング、
各フェーズ結果のコンパイルを担当します。

## 必要条件

- Git リポジトリ
- Python 3.11 以降
- Codex のコラボレーションツール
- 要求する並列度に足りるコラボレーションスロット

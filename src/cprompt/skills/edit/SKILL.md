---
name: edit
description: AI 向け Markdown プロンプト、Codex の SKILL.md、AGENTS.md 指示、サブエージェント用タスクテンプレートを作成・改訂する。プロンプト文面またはスキル指示が成果物のときに使用し、通常の人間向け文書には使用しない。
---

# プロンプトエディター

圧縮後も要求された挙動を保つ、簡潔な AI 向けプロンプトを作成する。

補助パスは、この `SKILL.md` を基準に解決する:

- プロンプト規律: `../../rules/prompt.md`
- 人間向け文書との境界: `../../rules/document.md`
- 雛形: `templates/{kind}.md`

## 入力

要求は、既存対象パスと編集要件、または新規ファイルの種別・対象パス・要件を指定する。種別が省略された場合は次のように推定する:

- 末尾が `SKILL.md` のパス → `skill`
- `AGENTS.md` または別の指示・ルール用 Markdown → `rule`
- spawn するエージェント向けの再利用可能な役割プロンプト → `agent`
- その他の AI 向け Markdown → `prompt`

Codex では Claude 形式の slash-command ファイルをスキルが置き換える。command の作成・移行を求められた場合は `skill` を作成し、最終報告で対応関係を説明する。

## オプションと作業先

- `--commit` — 検証後、今回の編集だけを commit する。
- `--worktree[=branch]` — 別 worktree で編集し、`--commit` を有効にする。

この skill の2階層上を絶対 `plugin_root` とし、`timestamp` を `YYYYMMDD-HHMMSS` で一度確定する。

`target` と各動的引数は引数配列の個別要素として渡す。shell command が必要な場合は、使用する shell に応じて値ごとに引用・エスケープし、例の引用符へ値を未処理で埋め込まない。

`--commit`（`--worktree` による有効化も含む）では、編集・worktree 作成前に起動元 checkout の repository 内 target に `git --literal-pathspecs status --porcelain -- "{target}"` を実行する。変更があればエラーで停止する。

`--worktree` では、root からの起動と、`..` 成分のない repository 相対 target を必須とする。絶対 target は拒否する。作成前に `git check-ignore -q -- "{target}"` を実行し、exit 0 は ignored target として拒否、exit 1 は続行、その他は不正な repository path として停止する。その後 `../../rules/worktree.md` の初期化・実行契約を適用する。編集対象が `target_dir` に存在しなければ、元 checkout のコピーを編集せず終了処理を行う。

`--worktree` がなければ相対 target は起動時の作業ディレクトリ基準で解決する。

## 出力制約

- ユーザーが指定した言語、または既存ファイルの言語を維持する。
- 要求が変更しない限り、機械可読 frontmatter、プレースホルダー、JSON フィールド名、ツール名、コード識別子を維持する。
- 未対応の Codex スキル frontmatter を追加しない。スキルには `name` と `description` が必要で、既存の対応済みフィールドだけを維持する。
- Markdown 出力の骨格を埋め込むと Markdown 内 Markdown が曖昧になる場合は、`templates/{name}.md` に外出ししてプロンプトから参照する。
- fenced code block 内のサブエージェント用タスク指示は、出力仕様そのものを除き、装飾的な見出しや強調を避けて平文とリストで書く。

## ワークフロー

1. `../../rules/prompt.md` を読む。対象が人間向け文書なら停止し、このスキルの対象外であることと文書ルールを使うべきことを報告する。
2. 新規ファイルでは `templates/` の対応する雛形を読み、要件に合わせて対象を作成する。編集では対象を読み、要求された変更を行う。
3. 適用されるプロンプト規律の各項目に対して結果を監査する。違反を `path:line` で記録して修正し、もう一度確認する。実質的な曖昧さが残る場合は意図を創作せずユーザーへ示す。
4. 結果を圧縮する。丁寧表現、重複、自明な指示、効果を言い換えただけの説明、挙動を変えない例を削除する。判断基準、安全境界、権限要件、フォールバック、入出力契約は残す。
5. 入力、分岐条件、失敗経路、副作用、出力を覆う解釈チェックリストを作る。作成したプロンプトだけを再読し、その記述からチェック項目へ回答する。不明瞭な項目を修正し、最大 3 回繰り返す。
6. 新規作成または大幅変更した Codex スキルは、利用可能な `skill-creator` の `quick_validate.py` で検証する。利用できない場合は YAML frontmatter、フォルダー名と `name` の一致、未完了プレースホルダーがないことを手動確認する。
7. 検証成功かつ `--commit` 指定時は、今回の変更パスだけを `git --literal-pathspecs add -- {paths}` で stage し、path を限定した `git --literal-pathspecs commit -- {paths}` で commit する。`{paths}` は各 path を個別引数として展開し、単一の連結文字列として渡さない。repository 外、Git が無視する file、`.codex/tmp/`、`.codex/worktrees/`、無関係な既存変更を含めず、既存 stage 状態を維持する。`git add -A` は使わず、対象変更がなければ commit しない。
8. worktree を作成した場合は、途中終了も含め `../../rules/worktree.md` の終了処理を行う。ただし今回作成・編集した ignored file が残る場合は削除せず、worktree とその file を報告する。branch、commit、残した worktree のパスを報告する。

ユーザーが委譲または独立したエージェント評価を明示的に求めた場合を除き、テスト用エージェントを spawn しない。委譲が許可され利用可能な場合は、評価者に対象プロンプトとチェックリストを渡し、意図した回答は渡さない。

## 報告

対象パス、修正した違反、圧縮による変更の有無、実行した検証、未解決のチェック項目を報告する。

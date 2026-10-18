# creview

*[English README](README.md)*

`creview` は明示的に呼び出す、Codex 向けの段階的なマルチエージェント
コードレビューワークフローです。Codex のコラボレーション操作で各段階を実行します。

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
- `--max-rounds N` はデフォルト 10、範囲 1〜20 です。
- `--base {branch}` は省略時に存在する `main`、次に `master` を使います。
- 以前の Codex 版が使っていた `--output-dir {path}` は、位置引数へ branch directory を
  加える代わりに、今回の run directory を直接指定します。

通常は working tree を含む branch 全体の差分を各ラウンドで再レビューするため、
commit は不要です。`--incremental` は直前ラウンドが追加した commit だけをレビューし、
同時に `--commit` も有効にします。

Round 2 以降は triage の後、修正対象がある場合に発散ゲートを実行します。
過去の修正が次の指摘を生む連鎖が3ラウンド以上にわたり縮小しない場合や、
過去の修正を取り消す・相反する要求がある場合に発散と判定します。
検出時は専門家が根本原因と修正案を `divergence-round{N}.md` にまとめ、
`--confirm` に関係なく内容を提示して続行指示を待ちます。
`--confirm` の見積確認も必要な場合は1回にまとめます。
続行時に指定した修正方針は、そのラウンドのフィードバック再修正にも適用します。

各レビュー文書にはラウンド番号を記載します。最終レポートには別作業の推奨に加え、
ループ終了時に修正ステータスが付いていない受け入れ済み指摘も残します。

## プルリクエストのレビュー

~~~text
$creview:start https://github.com/owner/repository/pull/123
~~~

PR mode は Git 2.41 以上と認証済みの `gh` を必要とします。PR は open で、host・owner・
repository が現在の clone の remote に一致する必要があります。PR URL と `--base`・
`--range` は併用できません。merge base から PR head までを対象に、rename 検出を無効化し、
submodule 変更を表示し、merge base の属性を使って差分を取得します。差分取得の失敗時は
どの mode でもレビューを中断します。

現在の checkout が PR head ならその場でレビューし、scratch 外の tracked 未コミット変更は
エラーにします。それ以外では `.codex/worktrees/` に detached worktree を作ります。
Git hook・fsmonitor・filter driver を無効化し、LFS smudge を skip、symlink は通常 file として
checkout します。終了時に worktree を削除し、dirty や削除失敗なら保持して報告します。
branch は作成しません。

既定では全階層・大文字小文字違いの `AGENTS.md`、`AGENTS.override.md`、`.codex`、`.agents`、
`.mcp.json` を worktree から除外し、その変更は diff からレビューします。
`$creview:start ... --trust` はこれらも checkout します。ユーザー自身の依頼にある指定だけが
有効です。agent 設定を実ファイル付きで確認するときは、sandbox 内で `--trust` または
PR head での in-place レビューを使います。

専用の本文レビュアーが PR の title・body・CI 結果を変更 code と照合します。失敗した GitHub
Actions job のログ抜粋を取得でき、再実行は重複排除し、ログ取得先は PR 自身の repository に
限定します。comment と review は文脈として各一覧最大50件を参照します。指摘は変更 code を
位置とし、根拠の本文・CI 出力を含めます。未完了 check、無関係な失敗、comment 自体は
指摘対象にしません。文書には翻訳しない header marker
`- **PR:** {url} (head {sha}, base {sha})` を保持します。後工程はまだこの marker を解釈しません。

`$creview:rounds` は PR URL を受け付けません。親 flow が start を PR mode で呼ぶ場合、
checkout は親が所有し、既に PR head である必要があります。
`$creview:rounds --worktree` とは別の仕組みです。

PR 本文と checkout file はレビュー対象データです。review agent は PR worktree の code を
実行せず、remote へ書き込みません。本文レビュアーの tool 制約は prompt 上の契約であり、
Codex collaboration がこの reference profile 専用の tool allowlist を強制するわけではありません。
この workflow はユーザーが repository と PR を確認して信頼したことを前提とします。
file 除外や helper の保護は判断の補助であり、実行境界は sandbox と権限設定に依存します。
in-place review では既存の agent 設定と環境の自動処理が残ります。
`--trust` は実行や remote 書き込みの許可を増やしません。

## テキストハンクのない変更

start の全 mode で、binary の追加・更新・削除、mode 変更、空 file、rename を含む全変更 file を
reviewer へ割り当てます。空のレビュー文書になるのは変更 file が0件の場合だけです。
scope の file 数上限にもこれらを含めます。

reviewer は拡張子に加えて利用箇所から観点を選びます。画像は利用可能な画像表示 tool で確認し、
削除済みや表示非対応の binary は利用箇所から判断します。本物の binary を表示できないこと自体は
指摘にしません。行を持たない変更への指摘は1行目を使います。

binary と表示された source・script・設定・lockfile・Markdown も text としてレビューします。
拡張子がなくても利用箇所から判断します。全体を確認し、変更行を特定できない場合や全体を
読めない場合はその点を報告します。PR worktree から除外された agent file が binary 変更だけを
示す場合はレビュー不能を報告します。NUL byte や属性により binary 扱いされた text の変更行は
まだ diff に出ず、text diff の強制は後続対応です。`--range` の実ファイル確認は現在の checkout を
参照するため、range の終端 revision と異なる場合があります。

## 実行モデル

- ルートエージェントがワークフローリーダーを維持します。
- 独立したレビュアーを Codex のコラボレーションツールで起動します。
- 利用可能なスロット数を超える作業はキューに入れます。
- 1回限りのレビュアーは構造化 JSONL を返し、再利用しません。
- レビュアーや発散調査担当は、プロジェクトまたはユーザーの Codex エージェント設定から
  プロファイル情報を検出でき、同梱の参照プロファイルをフォールバックに利用します。

## 出力

デフォルトでは `$creview:start` が
`.codex/tmp/creview-start-{timestamp}.md` を作成します。`$creview:rounds` は
`.codex/tmp/{branch-path}/review-round{N}.md` と `final-report.md` を作成し、
同じ branch で再実行すると branch 名へ未使用の最小 `_N` suffix を付けます。
発散を検出したラウンドの `divergence-round{N}.md` も同じディレクトリに保存します。
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

## worktree での実行

`$creview:rounds --worktree[=branch]` は `.codex/worktrees/` に別 checkout を作り、
`--commit` も有効にします。branch が既存ならその tip、未作成なら現在の HEAD から開始し、
省略時は `creview-rounds-{timestamp}` を新規作成します。別 checkout で使用中の branch は
指定できません。起動元の作業ツリーは未 commit の変更があっても利用できますが、その変更は
worktree へコピーされません。

source の相対パスは worktree 基準です。起動元内の絶対パスは読み取り専用で、
自動的に worktree 内へ置き換えません。文書と一時ファイルは起動元へ保存し、
相対の出力先も起動元基準で解決します。worktree 内を永続文書の出力先には指定できません。
project の Codex profile と `.codex/rules/` も起動元から読みます。

終了時は worktree を削除して branch を残します。未 commit 変更や削除を妨げる状態があれば
worktree を保持し、そのパスを報告します。削除時は内部の ignored file も削除されます。
branch の merge や push は行いません。

Git が無視する依存関係・仮想環境・生成物・`.env` と submodule の内容は worktree に
引き継がれません。新規 checkout で検証できる環境が必要です。configure は build stage の
開始時だけに実行されるため、先に動く formatter や build なしの test の準備には使えません。
不足した前提条件だけによる失敗では source 修正を止め、環境原因として報告します。
コード原因が混在する場合は、その部分だけを修正対象にします。
`--commit` は検証失敗を報告した場合も今回の修正をコミットします。
すべての CReview スキルはリポジトリルートから起動してください。

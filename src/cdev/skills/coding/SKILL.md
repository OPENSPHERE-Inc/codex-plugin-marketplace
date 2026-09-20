---
name: coding
description: 明示的に依頼されたマルチエージェントcoding workflowを常駐producerとreviewerで実行し、設計、実装、レビュー、QAを通す。ユーザーが CDev、複数agent、委譲、team workflowを求めた場合だけ使い、通常のcoding依頼では起動しない。
---

# マルチエージェントcoding

root team leader として振る舞う。作業を調整してgateを強制し、自分では設計・実装・レビューを行わない。

このskillには `spawn_agent`、`followup_task`、`wait_agent`、agent status確認が必要である。collaborationが利用できなければ停止する。ユーザーがこのskillを起動したか、委譲を求めた場合だけ実行する。

## runtimeとtrust

読み込まれたファイルから `skill_dir` を解決し、その2階層上を `plugin_root` とする。child taskには絶対パスを使う。`../../rules/teammate.md` を読む。

QA agentは移植先repositoryが宣言するcommandを実行する。信頼できるrepositoryでのみ実行し、network、credential、deployment、release権限を拡張しない。

オプション:

- `--review-rounds N` — producer/reviewer loop上限。デフォルト5、範囲1〜10。
- `--qa-attempts N` — QA/fix loop上限。デフォルト5、範囲1〜10。
- `--commit` — QA成功後、今回のsource pathだけをstageして簡潔なcommitを1つ作る。
- `--output {dir}` — 実行後も残す設計書の出力先directory。

`{timestamp}`を一度確定し、作業用の`{tmp_dir}`を`.codex/tmp/cdev-coding-{timestamp}/`とする。`{design_dir}`は`--output`の指定先、省略時は`.codex/tmp/cdev-coding-{timestamp}-design/`とする。相対パスは対象repositoryのrootから解決する。設計書専用のdirectoryを使い、repository root、sourceを含むdirectory、`{tmp_dir}`自身やその配下は指定不可とする。

開始前に`git status --porcelain -uall`を確認し、`.codex/tmp/`と明示された`--output`の指定先配下を除外する。残りにstaged、unstaged、untrackedの変更があれば停止し、commit、stash、または別workflowの選択をユーザーへ求める。

設計とfindingの文章はユーザーの言語で書き、field nameとseverity labelは英語で維持する。

## 常駐team

root leaderに加え、2つのpersistent childを使う:

- `cdev_reviewer_{timestamp}` — scope決定、設計・code review、comment review、QA。
- `cdev_producer_{timestamp}` — 設計、実装、review/QA fix。

各task nameは一度だけspawnする。完了したchildはidleだがcontextを維持する。次turnは`collaboration.followup_task`で開始し、実行中childへの補足だけ`send_message`を使う。必要な結果は`wait_agent`で待つ。具体的なfailureに一時specialistが必要な場合に備え、runtimeの空きslotを1つ残す。

## ワークフロー

1. `{design_dir}`、`{tmp_dir}/reviews`、`{tmp_dir}/qa`を作る。
2. `templates/team-analysis.md`、期待ID `d8760930-8d32-42c1-b033-d61f0cbd19c7`、変数`plugin_root`、task、output path `{tmp_dir}/team.jsonl`、document languageでreviewerをspawnする。`../../rules/agents-detection.md`を適用し、自己完結したtask summaryとproducer/reviewer profileを記録し、件数とpathだけを返す。
3. `team.jsonl`を読む。`templates/design.md`、期待ID `740fa1cf-fa38-40a0-85d0-4c9a99eab5de`、task summary、assigned scope、出力先`{design_dir}/design.md`、feedbackなし、選定producer profileでproducerをspawnする。以後のdesign review、改訂、codingではこのdesign pathを使う。
4. idle reviewerへ`templates/design-review.md`、期待ID `448ee08a-0284-4066-9de9-9f82e9078914`、design path、task、出力`{tmp_dir}/reviews/design-{round}.jsonl`を`followup_task`する。actionable findingがあれば、producerへdesign templateとfinding pathをfollow upし、再reviewする。`--review-rounds`で停止する。未解決Criticalはcodingをblockし、未解決Majorは最終報告へ残す。
5. `python "{plugin_root}/scripts/fetch_diff.py" snapshot {tmp_dir}/baseline-tree`でcoding前treeを記録する。
6. producerへ`templates/code.md`、期待ID `278bf9bd-53e2-4695-ad40-3fb91374519a`、承認済みdesign、implementation scope、test-suite flag、feedbackなしをfollow upする。changed pathと短いsummaryを返させる。
7. reviewerへ`templates/comment-review.md`、期待ID `8004286a-f4b2-4a6a-a3cb-9adc9ea370f2`、changed pathとdesignをfollow upする。commentだけを編集できる。
8. reviewerへ`templates/code-review.md`、期待ID `4abf814d-2e3e-4bec-8ff8-45c9a176b01f`、changed path、design、出力`{tmp_dir}/reviews/code-{round}.jsonl`をfollow upする。actionable findingがあればproducerへcode templateとfinding pathをfollow upし、comment/code reviewを繰り返す。上限で未解決CriticalがあればQAをblockし、未解決Majorは可視化する。
9. QAを`--qa-attempts`まで行う:
   - `python "{plugin_root}/scripts/fetch_diff.py" diff {tmp_dir}/baseline-tree {tmp_dir}/changes.txt`で今回のdiffを取得する。
   - `templates/qa.md`、同梱profile `../../references/agents/dev-helper.md`、期待ID `6a711cba-0da8-4177-a41f-ddb4cf2a6e1f`、temp path、diff path、attempt numberをreviewerへfollow upする。
   - 失敗時はproducerへcode template、`qa-result.jsonl`、`build.log`をfollow upし、comment review、code review、QAを繰り返す。
10. QA成功かつ`--commit`指定時は、producerとformatterが返したchanged pathから`.codex/tmp/`と`{design_dir}`を除外し、そのpathだけをstageしてcommitを1つ作る。除外pathが既にstageされていてもcommitに含めず、そのstage状態を維持する。対象pathがなければcommitしない。`git add -A`は使わない。
11. 最終QA summaryとreview件数を保持し、`python "{plugin_root}/scripts/del_tmp.py" "{tmp_dir}"`で`{tmp_dir}`だけを削除する。`{design_dir}`と設計書は残す。

設計書のpath、team task name、design/code review round、変更ファイル、未解決finding、QA結果とwarning、該当時のcommit hash、gateを停止したfailureを報告する。

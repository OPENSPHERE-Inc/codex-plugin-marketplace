# persistent teammate契約

cdevのproducerとreviewerへ適用する。

## 権限とscope

- ユーザーが明示したcoding taskとrepository内だけで作業する。
- producerは割り当てられたdesign documentとsource scopeを編集できる。reviewerはdesign/code review中はread-only、comment reviewではcommentだけ、QAではformatterによる変更だけを行える。
- ユーザーが明示的に許可しleader taskに含めない限り、commit、deploy、publish、credential access、network使用を行わない。
- leaderが狭いnested taskを明示し空きcollaboration slotがある場合を除き、別agentをspawnしない。

## persistent turn

- 最初の`spawn_agent`でpersistent teammateになる。1 turnにつき割り当てられたtemplateを1つ完了し、final answerでroot leaderへ結果を返す。
- leaderはidle teammateを`followup_task`で再開する。以前のcontextを維持しつつ、各follow-upを新しいbounded taskとして扱う。
- `send_message`は実行中の相手への追加情報にだけ使う。idle teammateは起動しない。
- 別teammateへ直接messageしない。root leaderがreview findingをfileとfollow-up taskで中継する。
- path、counter、changed-file list、短いsummaryを返す。詳細findingとstructured dataは割り当てられたfileへ書く。

## template契約

行動前にtask templateの絶対パスを読む。渡された全`{{...}}`値と任意profile pathを適用する。templateの`template_id`を変更せず返す。JSONL出力は1行1objectとし、`python "{{plugin_root}}/scripts/check-jsonl.py" {path}`で検証する。

書き込みにはrepository編集toolを使い、shell heredocを使わない。scopeに応じて同じdirectoryの`comment.md`、`document.md`、`review.md`へ従う。

## finding gate

- `Critical`: designまたはimplementationがtaskを安全に満たせない。次gate前に解決必須。
- `Major`: correctness、security、compatibility、maintainabilityの重大な欠陥。review-round上限内で修正するか未解決として報告する。
- `Minor`と`Info`: 記録するが、ユーザーが引き上げない限りgateをblockしない。

producerは各Critical/Majorを修正するか、sourceに基づく却下理由を記録する。reviewerは次のreview turnで修正と却下を検証する。

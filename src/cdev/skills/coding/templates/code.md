---
name: code
description: persistent producerとして承認済みCDev designを実装し、review/QA fixを適用する。
template_id: 278bf9bd-53e2-4695-ad40-3fb91374519a
---

`{{plugin_root}}/rules/teammate.md`、任意の`{{profile_path}}`、`{{design_paths}}`の全file、`(none)`でない場合は`{{feedback_path}}`を読む。

Task: `{{task}}`
Assigned scope: `{{assigned_scope}}`
Test-driven: `{{tdd}}`
QA result/log: `{{qa_paths}}`（QA fix以外は`(none)`）

assigned scope内だけを実装する。各Critical/Major review itemを修正するか、sourceに基づく却下をreturn summaryへ記録する。test suiteがある場合は実装前または同時にtestを追加・更新し、passさせるためにtestを弱めない。repository instructionと`{{plugin_root}}/rules/comment.md`に従う。

`{changed_paths, comments_changed, rejected_findings, summary_line, template_id}`を返す。変更した全source/test pathを列挙し、template IDを維持する。

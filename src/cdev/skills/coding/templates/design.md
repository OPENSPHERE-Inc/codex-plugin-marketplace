---
name: design
description: persistent producerとしてCDev implementation designを作成・改訂する。
template_id: 740fa1cf-fa38-40a0-85d0-4c9a99eab5de
---

`{{plugin_root}}/rules/teammate.md`と、nullでない場合は`{{profile_path}}`を読む。

Task: `{{task}}`
Assigned scope: `{{assigned_scope}}`
Design path: `{{output_path}}`
Review feedback: `{{feedback_path}}`（初回は`(none)`）

sourceを編集せずscope内の既存codeを調べる。初回はapproach、対象file/module、interface/data shape、edge case/error handling、compatibility、test/build影響を覆う簡潔なdesignを書く。改訂時はfinding JSONLを読み、各Critical/Majorを修正するかsourceに基づく却下をdesignへ記録し、無関係なsectionを安定させる。`{{plugin_root}}/rules/document.md`に従う。

`{path, changed, summary_line, template_id}`を返す。template IDを維持する。

---
name: comment-review
description: CDev producerが変更したcommentだけをreview・修正する。
template_id: 8004286a-f4b2-4a6a-a3cb-9adc9ea370f2
---

`{{plugin_root}}/rules/teammate.md`、`{{plugin_root}}/rules/comment.md`、`{{design_paths}}`のdesign file、`{{changed_paths}}`の変更fileを読む。

untracked fileを含め、今回追加・変更されたcommentを特定する。明白なcodeの言い換え、chat/change history依存、長い正当化、FIXME/TODOの誤用を削除・圧縮する。実行logicを変更しない。変更commentが無ければ編集しない。

template IDを維持し、`{reviewed_paths, fixed_count, template_id}`を返す。

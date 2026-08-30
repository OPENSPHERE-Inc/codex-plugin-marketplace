---
name: qa
description: 信頼できるrepositoryのformat/build/testを1回実行し、構造化CDev QA resultを記録する。
template_id: 6a711cba-0da8-4177-a41f-ddb4cf2a6e1f
---

`{{plugin_root}}/rules/teammate.md`、`{{plugin_root}}/rules/build-format-detection.md`、任意の`{{profile_path}}`、`{{diff_path}}`を読む。

Run directory: `{{tmp_dir}}`
Attempt: `{{attempt_num}}`

repositoryの信頼済みformat/build/test commandを解決する。各commandをrepository rootから個別に実行し、shell separatorやpipeで合成しない。関連outputを`{{tmp_dir}}/build.log`へ記録する。source変更はformatter auto-fixだけに限定する。

diffがstageへ影響しない場合だけskipする。workflow未宣言ならread-onlyのvisual syntax/symbol checkを行い、`.codex/rules/build-format.md`を推奨するwarningを設定する。

失敗時はstage、簡潔なerror summary、対象file、fix direction、`{{plugin_root}}/rules/agents-detection.md`による最も近いspecialist profileを特定する。

`{{tmp_dir}}/qa-result.jsonl`へJSON objectを1つ書く:

```json
{"workflow_source":"build-format.md|AGENTS.md|README.md|none","workflow_warning":null,"format":{"format_violations_fixed":0},"build":{"ran":true,"success":true},"test":{"ran":true,"success":true},"failure":null}
```

失敗時の`failure`は`{stage, error_summary, error_files, suggested_profile: {name, profile_path}|null, fix_guidance, log_path}`。fileを検証し、`{path, success, summary_line, workflow_warning, template_id}`を返す。

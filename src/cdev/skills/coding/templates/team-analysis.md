---
name: team-analysis
description: CDev taskをscopeし、常駐Codex teamのproducer/reviewer profileを選定する。
template_id: d8760930-8d32-42c1-b033-d61f0cbd19c7
---

`{{plugin_root}}/rules/teammate.md`と`{{plugin_root}}/rules/agents-detection.md`を読む。taskをscopeするために必要な範囲だけrepositoryを調査し、sourceを編集しない。

Task: `{{task}}`
Output: `{{output_path}}`

対象言語、影響path/subsystem、build/test surface、test suiteの有無を判定する。`{{doc_lang}}`で自己完結した`task_summary`を作る。

次を選定する:

- Producer profile: 検出profileがtaskを不適切に狭めず実装を明確に支援する場合を除き、通常は`general`。
- Reviewer profile: 主なcorrectness/risk surfaceに最も近いspecialist。該当なしは`general`。

`{{output_path}}`へJSON objectを1つ書く:

```json
{"task_summary":"...","target_languages":["..."],"has_test_suite":true,"scope":["path/or/subsystem"],"producer":{"name":"general","profile_path":null,"reason":"..."},"reviewer":{"name":"...","profile_path":"... or null","reason":"..."},"rationale":"..."}
```

fileを検証し、frontmatter IDを変更せず`{path, target_languages, has_test_suite, template_id}`を返す。

---
name: code-review
description: persistent reviewerとしてCDev implementation changeをreviewし、gate findingを書く。
template_id: 4abf814d-2e3e-4bec-8ff8-45c9a176b01f
---

`{{plugin_root}}/rules/teammate.md`、`{{plugin_root}}/rules/review.md`、任意の`{{profile_path}}`、`{{design_paths}}`の全file、`{{changed_paths}}`の全fileを読む。sourceを編集しない。

Task: `{{task}}`
Output: `{{output_path}}`

task/designに対するcorrectness、欠けたedge case/error handling、security、concurrency、performance、compatibility、test、maintainabilityをreviewする。実在する`file:line`を使う。

JSON objectを1つ書く:

```json
{"findings":[{"severity":"Critical|Major|Minor|Info","location":"file:line","issue":"...","fix_direction":"..."}],"critical":0,"major":0,"minor":0,"info":0}
```

proseは`{{doc_lang}}`で書く。fileを検証し、`{path, critical, major, minor, info, template_id}`を返す。

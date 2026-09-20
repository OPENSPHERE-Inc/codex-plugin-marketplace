---
name: design-review
description: persistent reviewerとしてCDev designをreviewし、gate findingを書く。
template_id: 448ee08a-0284-4066-9de9-9f82e9078914
---

`{{plugin_root}}/rules/teammate.md`、`{{plugin_root}}/rules/review.md`、任意の`{{profile_path}}`を読む。designやsourceを編集しない。

Task: `{{task}}`
Design: `{{design_path}}`
Output: `{{output_path}}`

`{{plugin_root}}/rules/divergence.md`を読み、reviewer節に従って発散パターンを検出する。task completeness、feasibility、interface/data shape、edge case、error handling、compatibility、testability、regression riskを判断する。JSON objectを1つ書く:

```json
{"findings":[{"severity":"Critical|Major|Minor|Info","location":"section or file","issue":"...","fix_direction":"..."}],"critical":0,"major":0,"minor":0,"info":0}
```

finding proseは`{{doc_lang}}`で書く。fileを検証し、`{path, critical, major, minor, info, template_id}`を返す。

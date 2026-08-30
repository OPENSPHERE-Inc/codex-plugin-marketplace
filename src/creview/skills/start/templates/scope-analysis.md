---
name: scope-analysis
description: レビュー差分を上限付きスコープへ分割し、関連する Codex specialist profile を選定する。
template_id: b3e2f1a7-9c84-4d56-8e3b-7f1a4c9d2e85
---

`{{tmp_dir}}/diff.txt` を読み、変更行数を数え、差分をレビュースコープへ分割して専門視点を選定する。最初に `{{plugin_root}}/rules/sub-agent.md` と `{{plugin_root}}/rules/agents-detection.md` を読む。

ユーザー指定レビュアー: `{{user_requested}}`（空の場合がある）。

## スコープ構築

1. 変更パス、言語、subsystem、risk area を判定する。`line_count` は追加行と削除行の合計とする。
2. 変更行が 800 以下かつ 20 ファイル以下なら 1 スコープにする。
3. それ以外は凝集性でまとめた後、可能な限り各スコープを変更 400 行以下かつ 10 ファイル以下にする。1 ファイルを分割しない。最大 8 スコープとし、上限超過時は理由を説明する。
4. 各変更ファイルを正確に 1 スコープへ割り当て、安定したパス順で `s1`、`s2`、... と命名する。

## レビュアー選定

各スコープに specialist-profile 検出ルールを適用する。実質的に関連する各 profile を `{name, profile_path, reason}` として追加する。該当が無ければ `{name: "general", profile_path: null, reason: "no matching specialist profile"}` を 1 つ使う。ユーザー指定レビュアーは重複しない限り全スコープへ追加し、可能なら profile path を解決する。

`{line_count, scopes: [{scope_id, paths, line_count, reviewers: [{name, profile_path, reason}]}], extension_summary, rationale, template_id}` を返す。frontmatter の `template_id` を変更せず返す。

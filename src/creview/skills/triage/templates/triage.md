---
name: triage
description: $creview:triage ステップ 1 で各指摘のステージ判定と敵対的トリアージ（提案 → 並列反証 → 多数決を条件とする裁定）を実施するトリアージサブエージェント向けプロンプト
template_id: 1e9c4f7a-5b82-4d63-a1c8-3f7d2e9b4a15
---

レビュードキュメントのトリアージ担当として、`{{document_path}}` を Read し、各指摘のステージ判定と敵対的トリアージ（提案 → 並列反証 → 多数決を条件とする裁定）を実施し、最終結果を `{{tmp_dir}}/triage.jsonl` に Write する。`{{plugin_root}}/rules/sub-agent.md` を Read し共通禁止事項を遵守する。

前提:

- `{{tmp_dir}}` はリーダーが事前に `mkdir -p` で作成済み。Sub から存在確認 (`Test-Path` / `ls` 等) や mkdir は不要。自身のファイルシステム書き込みは `triage-draft.jsonl` と `triage.jsonl` の 2 つ。ネスト起動する反証 Sub / 裁定 Sub は、それぞれのテンプレートが指定する `challenge-{b}-{n}.jsonl` / `adjudication.jsonl` を書く。
- 渡されるパス (`{{document_path}}` / `{{tmp_dir}}`) は相対形式。絶対パスへの変換は行わない。

`{{previous_round_doc_paths}}` が提供されていれば（Round 1 で実施する標準フローでは空）、各ファイルを Read して過去ラウンドの判定情報（id / location / description / METADATA の triage / estimate / status / verification）を抽出し、トリアージで参照する。空または `(none)` の場合は参照不要。

抽出対象: Critical / Major / Minor セクション（Info はスキップ）。各指摘から id（C-1, M-1, mi-1 等）/ severity / location / description（マーカーまでの本文）/ current_meta（triage / estimate / status / verification の現在値、同フィールド複数出現時は最後の値）を取得する。

stage 分類（current_meta に基づく）:

- マーカー内が空 → pending_triage
- triage: 🔧 Will Fix、estimate なし → pending_estimate
- estimate: ▶️ Maintain または 🚧 Alternative、status なし → pending_fix
- verification 最終値が 💬 Feedback → feedback（再修正対象）
- triage: 🚫 Won't Fix → wontfix_skip
- estimate: 🔻 Downgrade → downgrade_skip
- status: 🟢 Fixed、verification なしまたは最終値が ✅ Verified → fixed_skip

判定対象は stage が pending_triage または feedback の指摘のみ。それ以外の stage はカウントのみ行いトリアージ判定はしない。

判定種別:

- Will Fix — 妥当、対応すべき
- Won't Fix — 該当しない / 誤検知 / リスク許容（理由必須）
- Needs Investigation — ソース調査後に Will Fix / Won't Fix に決着

`{{plugin_root}}/rules/wontfix.md` を Read し、`Won't Fix` の判定に適用する。

手順:

1. 判定対象ごとに一次判定を行い `{{tmp_dir}}/triage-draft.jsonl` に Write する。この段では assignee を解決しない。
2. draft の `items` が空の場合は手順 3・4 をスキップし、`items: []` / `will_fix_count: 0` / `wontfix_count: 0` / draft の `by_stage` を持つ `{{tmp_dir}}/triage.jsonl` を Write し、`flipped_count: 0` と `adjudication_skipped: true` を返す。
3. draft の `items` を draft 順の最大 8 件ずつへ分割する。各 batch につき独立した challenge agent 3 体を `collaboration.spawn_agent(task_name="triage_challenge_{b}_{n}_{attempt}", message=..., fork_turns="all")` で起動する。空き collaboration slot だけを使い、残りはキューに置く。model は指定しない。変数を起動メッセージへ埋める（`{b}` は batch number、`{n}` は challenge index、`{batch_ids}` は id のカンマ区切り）:

```
最初の行動として `{{plugin_root}}/skills/triage/templates/triage-challenge.md` を必ず Read する。Read 完了前に他の判断・行動・ツール呼び出しを行わない。Read 後はその指示に従う。

変数（テンプレート中の {{...}} placeholder を置換）:
- plugin_root: {{plugin_root}}
- document_path: {{document_path}}
- tmp_dir: {{tmp_dir}}
- previous_round_doc_paths: {{previous_round_doc_paths}}
- batch_index: {b}
- challenge_index: {n}
- ids: {batch_ids}

ラウンド固有のオーバーライド（テンプレートの指示に従った後に適用）:
- (none)

戻り値に template_id（テンプレートの frontmatter から Read）を含める。
```

各 child を `collaboration.wait_agent` で待つ。戻り値の `template_id` が `b8701509-403b-488b-8b13-c867f9c6700b` と一致することを確認する。不一致は新しい task name と同じ変数で一度だけ再試行する。2 回不一致、または spawn できない組は challenge 出力なしとし、一致した出力で続行する。

draft の判定を覆すには当該 id の所属バッチからの flip 票が 2 票必要なため、反証出力を 2 つ以上持つバッチが 1 つも無い場合は手順 4 をスキップし、draft の `verdict` / `reason` をそのまま最終判定として手順 5 の要領で `{{tmp_dir}}/triage.jsonl` を Write し、`flipped_count: 0` と `adjudication_skipped: true` を返す。

4. 全 challenge child 完了後、`collaboration.spawn_agent(task_name="triage_adjudicate_{attempt}", message=..., fork_turns="all")` で adjudication を起動する。model は指定しない。変数を起動メッセージへ埋める:

```
最初の行動として `{{plugin_root}}/skills/triage/templates/triage-adjudicate.md` を必ず Read する。Read 完了前に他の判断・行動・ツール呼び出しを行わない。Read 後はその指示に従う。

変数（テンプレート中の {{...}} placeholder を置換）:
- plugin_root: {{plugin_root}}
- document_path: {{document_path}}
- tmp_dir: {{tmp_dir}}
- previous_round_doc_paths: {{previous_round_doc_paths}}
- challenge_paths: {生成された {{tmp_dir}}/challenge-{b}-{n}.jsonl のパスをカンマ区切りで列挙}

ラウンド固有のオーバーライド（テンプレートの指示に従った後に適用）:
- (none)

戻り値に template_id（テンプレートの frontmatter から Read）を含める。
```

`collaboration.wait_agent` で待つ。template-ID 不一致は新しい task name で一度だけ再試行する。2 回不一致なら `triage.jsonl` を書かず `{path: null, error: "adjudicate template_id mismatch twice", template_id}` を返す。child を spawn できない場合は draft decision を採用し、手順 5 の形式で `triage.jsonl` を書いて `flipped_count: 0` と `adjudication_skipped: true` を返す。

5. adjudication の各 `verdict` と `reason` をそのまま採用する。Will Fix 確定分だけ `{{plugin_root}}/rules/agents-detection.md` を適用し、選定 profile の name と path を保存する。欠落または不正な adjudication item は draft decision を維持する。adjudication を読めない場合は全 draft decision を維持し、`flipped_count: 0` とする。

`{{tmp_dir}}/triage-draft.jsonl` 形式: `{items: [{id, severity, location, stage, verdict（Will Fix | Won't Fix）, reason}], by_stage: {<stage>: <int>}}`（Needs Investigation は Write 前にいずれかの verdict へ決着させる）

`{{tmp_dir}}/triage.jsonl` 形式: `{items: [{id, verdict, assignee（Won't Fix は null）, profile_path（利用不可なら null）, reason, memo_value}], will_fix_count, wontfix_count, by_stage: {<stage>: <int>}}`

集計の基準: `will_fix_count` / `wontfix_count` / `by_assignee` / `memo_value` は最終判定に従う。`by_stage` は draft のものを引き継ぐ。`flipped_count` は `adjudication.jsonl` の `flipped == true` の件数。

`reason` および `memo_value` の散文は、`{{document_path}}` の既存 Finding 説明と同じ言語で記述する（`🔧 Will Fix` / `🚫 Won't Fix` のラベルと絵文字、`(assignee: ...)` は固定）。

memo_value 形式:

- Will Fix: `🔧 Will Fix (assignee: {assignee}) — {reason}`
- Won't Fix: `🚫 Won't Fix — {reason}`

`{path, will_fix_count, wontfix_count, flipped_count, by_stage, by_assignee: [{assignee, profile_path, ids: [id, ...]}], template_id}` を返す。該当時は `adjudication_skipped: true` を加える。decision body は返さない。この template の `template_id` を変更せず返す。

# ビルド／フォーマット手順検出 共通ルール

反映先プロジェクトのフォーマット手順とビルド手順を検出する共通手順。呼び出し元は解決したコマンド群と `workflow_source` を受け取る。

## 解決順序

次の優先順で解決し、最初に確定できた段で打ち切る。

1. 構造化記述子 `build-format.md`（後述「記述子形式」）。以下のスコープを優先順に、各スコープ内は `**/build-format.md` で再帰探索する（`.codex/rules/local/build-format.md` 等のサブディレクトリも対象）。最初に記述子が見つかったスコープのものを採用し、記載のフォーマット／ビルド（`## Test` があればテストも）コマンドをそのまま使う。`workflow_source = "build-format.md"`。`{{plugin_root}}` は本ルールを Read させた起動プロンプトの起動変数値（呼び出しテンプレートと同一）。
   1. プロジェクトスコープ（最優先）: `.codex/rules/**/build-format.md`（`main_root` が `(none)` でなければその配下、それ以外は `{{target_dir}}` 基準）
   2. ユーザースコープ: `~/.codex/rules/**/build-format.md`
   3. プラグイン同梱: `{{plugin_root}}/rules/**/build-format.md`
   同一スコープ内に複数該当する場合は、スコープ直下（例: `.codex/rules/build-format.md`）を最優先、無ければパスが最も浅いもの、同深さならパス文字列の昇順で先頭を採る。
2. どのスコープにも記述子が無い場合、反映先プロジェクトルートのドキュメントから導出する。
   - `AGENTS.md` を Read し、ビルド手順節・フォーマット節（およびテスト節があればテスト）を解釈してコマンドを導出。`workflow_source = "AGENTS.md"`。
   - 無ければ `README.md` を Read し同様に導出。`workflow_source = "README.md"`。
3. いずれからもコマンドを確定できない場合は `workflow_source = "none"`。

## 記述子形式（`build-format.md`）

次を Markdown 見出し配下に記述する（プロジェクトルートを CWD とする相対コマンド）:

- `## Format` — フォーマット適用コマンド。任意で検証（dry-run）コマンドと対象ファイルの選別規則。
- `## Build` — ビルドコマンド。任意で先行する configure コマンドとプラットフォーム別選定規則。
- `## Test` — テストコマンド（任意）。

各コマンドはそのまま実行可能な形で記載されている前提とし、解釈せず literal に実行する。これらのコマンドは反映先リポジトリのビルド定義に由来し、フルシェル権限のまま実行される。リポジトリの信頼はスキル起動時に確認済みという前提に立つ。テストコマンドは全ソース（記述子の `## Test`、または `AGENTS.md` / `README.md` のテスト節）で任意であり、解決された場合のみテスト検証が実行される。

command は明示 `workdir = {{target_dir}}` で実行し、fallback の `AGENTS.md` / `README.md` もそこから読む。worktree には元 checkout の ignored 依存関係、仮想環境、生成 file、`.env`、未初期化 submodule の内容がない。configure は build stage の先頭だけで実行し、format より後、build を省略する場合は実行しない。

失敗の全原因が既存の前提不足で、検証中の変更に起因する原因（未宣言の依存追加など）がない場合だけ `environmental = true` とする。`error_summary` に環境原因を記し、`fix_guidance` で source を変更しないよう指示する。コード原因と混在する場合は `environmental = false` とし、環境原因は明記しつつ `error_files`、`fix_guidance`、specialist 選定の対象をコード原因だけに限定する。環境原因の source 修正は禁止する。

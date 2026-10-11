# worktree とパスの契約

出力作成・子の起動前に適用する。呼び出し元 skill が `timestamp` を一度確定する。

## 初期化

- 上位から `target_dir` と `main_root` が渡された場合は維持し、別 worktree を作らない。
- それ以外では Git repository root からの起動を必須とする。`git rev-parse --show-prefix` が空でなければ書き込み前にエラーで停止する。`git rev-parse --show-toplevel` の絶対パスを `target_dir` とし、`main_root = (none)` とする。
- `--worktree[=branch]` 指定時は `--commit` を有効にする。`=branch` 省略時は `{skill-name}-{timestamp}` とし、`skill-name` は `cdev-coding`、`creview-rounds`、`cprompt-edit` のいずれか。明示された空の branch は拒否する。
- 上位から作業先を引き継がず、`--worktree` を指定した場合だけ、起動元 root で `python "{plugin_root}/scripts/worktree.py" create "{branch}"` を実行する。JSON `{main_root, worktree_path, branch}` を読み、`target_dir = worktree_path` としてこの worktree の管理元になる。既存 local branch はその tip、未作成 branch は HEAD から開始する。別 checkout で使用中の branch は拒否される。
- 作成失敗時、helper は登録の帰属を証明できないため、clean な hook 失敗も含め登録済み target を保持する。未登録で予約の同一性を確認できる空ディレクトリだけを `rmdir()` で回収する。失敗したコマンド、保持先の絶対パス、要求 branch、保持理由を報告して停止し、元 checkout の編集へ切り替えない。要求 branch を実際の登録 branch とみなさない。再試行前に原因を解消し、保持先を確認して明示的に通常削除する。強制削除や保持先の無条件な自動削除は行わない。
- `main_root` が `(none)` でなければ `metadata_root = main_root`、それ以外は `target_dir` とする。skill の一時パスと相対の文書・出力先は `metadata_root` 基準で解決し、使用前に絶対パスへ変換する。worktree 使用時はその中の永続出力先を拒否する。

## 実行と委譲

- source、Git、helper、format、build、test command は実行 tool の明示 `workdir = target_dir`（または同等機能）で実行する。その場所で `git rev-parse --show-toplevel` が `target_dir` と一致することを確認する。shell の `cd` で別 tool call や child の作業先が変わると仮定しない。
- source path は `target_dir` 基準で解決し、読み書きには絶対パスを使う。task が指定したパスを維持し、元 checkout 内の絶対パスを worktree 内へ書き換えない。そのパスは割り当てられた出力先でない限り read-only とする。
- nested launch を含む全 spawn・follow-up に絶対 `plugin_root`、`target_dir`、`main_root`（または `(none)`）、一時パス、出力パスを渡す。child も同じ明示作業先を使い、この契約をそのまま引き継ぐ。
- 対象 checkout の repository 指示を適用する。project Codex profile と `.codex/rules/` は `metadata_root` 配下で検出する。build 手順の fallback `AGENTS.md` / `README.md` は `target_dir` から読む。
- source の書き込みは `target_dir` 内、成果物は割り当てられた一時・出力パス内に限定する。包含判定では `..` 成分と symlink による逸脱を拒否し、パス成分で比較する。Windows の区切り文字とドライブ文字の大小は同一視する。task 固有の read-only・編集範囲制約も適用する。
- source の stage から `.codex/tmp/`、`.codex/worktrees/`、割り当てられたレポート・設計書の出力先を除外する。無関係な変更と既存 stage 状態を維持する。worktree mode は commit 済み file から開始し、未 commit 変更、ignored 依存関係、secret、submodule 内容をコピーしない。

## 終了

worktree を作成した skill だけが削除する。全 child の終了、必要な commit、永続出力の完了後、途中終了時も `workdir = main_root` で `python "{plugin_root}/scripts/worktree.py" remove "{worktree_path}"` を実行する。強制削除せず、拒否時は worktree を保持してパスと理由を報告する。Git の削除では内部の ignored file も削除される。branch は残し、名前と commit hash を報告する。merge や push は行わない。

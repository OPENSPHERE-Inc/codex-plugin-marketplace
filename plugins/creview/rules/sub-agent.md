# Sub-Agent Contract

Apply these rules to every sub-agent launched by a creview skill.

## Authorization and scope

- creview delegation is allowed only when the user explicitly invokes a creview skill or explicitly requests a parallel or multi-agent review workflow.
- Write only the output paths assigned by the launch template.
- Source edits are allowed only for fix, build-fix, comment-review, and formatter tasks, and only within the scope assigned to that task. All other review tasks are read-only.
- A child launched by a sub-agent inherits its parent's write and side-effect limits.
- Run build, test, formatter, network, commit, or other state-changing commands only when the template and the user's authorization permit them.

## One-shot launch

- Use `collaboration.spawn_agent` with a unique lowercase `task_name`, a complete `message`, and the smallest useful `fork_turns` value. Use `fork_turns="all"` when the child needs the user's full task context.
- Respect the runtime concurrency limit. Queue excess work and start it after a running child finishes.
- Wait for completion with `collaboration.wait_agent`. A child's final answer is delivered to its parent automatically.
- Do not use `collaboration.send_message` or `collaboration.followup_task` for a one-shot task. Retry by spawning a fresh uniquely named child.
- Do not provide a model or reasoning override unless the user or applicable repository instructions require one.

## Launch message

Include all of the following:

1. The absolute path of the external template and an instruction to read it before acting.
2. Every value for the template's `{{...}}` placeholders, including the absolute `plugin_root`.
3. Round-specific overrides, explicitly `(none)` when absent.
4. The expected `template_id` and a requirement to return it unchanged.
5. An optional specialist profile path. When present, read it after the task template and apply its domain perspective without expanding the assigned scope.

Do not quote or paraphrase the template body in the launch message. If the returned `template_id` does not match, retry once with a new task name. Abort and report the mismatch after a second failure.

## File output

- Use the available repository editing tool for file writes; do not construct shell heredocs.
- A `.jsonl` output described as one object must contain exactly one JSON object on one line.
- Validate JSONL with `python "{{plugin_root}}/scripts/check-jsonl.py" {path}` and fix any error before returning.
- Preserve field names, structural Markdown anchors, finding IDs, severity labels, and emoji required by the template.

## Shared conventions

When editing code, read `comment.md` beside this file. When editing human-facing documentation, read `document.md` beside this file.

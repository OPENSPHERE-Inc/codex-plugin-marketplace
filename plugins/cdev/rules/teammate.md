# Persistent Teammate Contract

Apply this contract to the cdev producer and reviewer.

## Authorization and scope

- Work only inside the user's explicit coding task and repository.
- The producer may edit its assigned design document and source scope. The reviewer is read-only during design/code review, may edit comments during comment review, and may apply formatter-only changes during QA.
- Do not commit, deploy, publish, access credentials, or use the network unless the user explicitly authorized that action and the leader's task includes it.
- Do not spawn another agent unless the leader explicitly assigns a narrowly scoped nested task and a collaboration slot is available.

## Persistent turns

- The initial `spawn_agent` creates a persistent teammate. Complete one assigned template per turn and return the result to the root leader in the final answer.
- The leader resumes an idle teammate with `followup_task`. Treat every follow-up as a new bounded task while retaining prior context.
- `send_message` is only for additional information delivered while the recipient is still running. It does not wake an idle teammate.
- Do not message another teammate directly. The root leader routes review findings through files and follow-up tasks.
- Return paths, counters, changed-file lists, and a short summary. Put detailed findings and structured data in the assigned file.

## Template contract

Read the absolute task-template path before acting. Apply every supplied `{{...}}` value and the optional profile path. Return the template's `template_id` unchanged. On a JSONL output, write one JSON object on one line and validate it with `python "{{plugin_root}}/scripts/check-jsonl.py" {path}`.

Use repository editing tools for writes, not shell heredocs. Follow `comment.md`, `document.md`, and `review.md` beside this file when their scopes apply.

## Finding gates

- `Critical`: the design or implementation cannot safely satisfy the task; must be resolved before the next gate.
- `Major`: significant correctness, security, compatibility, or maintainability defect; fix within the review-round cap or report it unresolved.
- `Minor` and `Info`: record but do not block a gate unless the user elevates them.

The producer responds to each Critical/Major item by fixing it or recording a source-grounded rejection. The reviewer verifies fixes and rejections in the next review turn.

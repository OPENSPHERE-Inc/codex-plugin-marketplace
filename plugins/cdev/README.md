# cdev

*[日本語版 README](README_ja.md)*

`cdev` implements a coding task through an explicitly invoked Codex
multi-agent workflow. The root agent coordinates two persistent workers: a
producer and an independent reviewer.

## Invocation

~~~text
$cdev:coding Implement the requested feature, run the repository checks, and
leave the changes uncommitted.
~~~

State important constraints in the request, including scope, required checks,
whether commits are allowed, and any files that must remain untouched.

- `--review-rounds N` caps each design or code producer/reviewer loop.
  Default: 5; range: 1–10.
- `--qa-attempts N` caps the QA/fix loop. Default: 5; range: 1–10.
- `--commit` commits this run's changes after QA succeeds. Without it, no commit is made.

## Workflow

1. Confirm repository instructions, task scope, and a clean starting worktree.
2. Start one persistent producer and one persistent reviewer.
3. Analyze the team and prepare a design.
4. Iterate design and design review until the gate passes.
5. Implement the design, review comments and code, and address findings.
6. Run the repository's relevant verification and an independent QA gate.
7. Commit only when the user explicitly requests it.

The same two child agents are resumed for later phases, preserving context
while leaving one collaboration slot available to the root workflow. If the
runtime has fewer slots, work is queued.

## Safety and output

- A clean Git worktree is required at the start so user changes are not
  mistaken for workflow output.
- Repository and user Codex agent profiles may inform role prompts; bundled
  reference profiles provide a fallback.
- Intermediate files are written only below `.codex/tmp/`.
- The workflow follows the destination repository's `AGENTS.md`, formatting,
  build, and test instructions.

## Requirements

- Git repository
- Python 3.11 or later
- Codex collaboration tools
- Project-specific build and test dependencies

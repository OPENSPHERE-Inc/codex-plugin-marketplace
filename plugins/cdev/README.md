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
- `--output {dir}` sets the design document directory, defaulting to
  `.codex/tmp/cdev-coding-{timestamp}-design/`. Relative paths resolve from the destination
  repository root. The repository root, directories containing source files, and the run's
  disposable working directory or its descendants are not valid destinations.

The design document `{design_dir}/design.md` is kept after the run, and the final report lists
its path. The working directory `.codex/tmp/cdev-coding-{timestamp}/` is deleted after the run.
`--commit` excludes `.codex/tmp/` and the design directory from staging.

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

Design creation, revision, and review follow the [divergence prevention rule](rules/divergence.md).
They address undecided specifications or invariants, problem classes that cannot be closed by
individual case fixes, unadjudicated requirement conflicts, and mismatches with the existing design.
The reviewer raises matches as Major or higher and does not raise counterexamples outside the
design's stated accepted scope. It challenges the scope itself only if the task cannot be met within it.

## Safety and output

- A clean Git worktree is required at the start so user changes are not
  mistaken for workflow output. This check excludes `.codex/tmp/` and the explicitly supplied
  `--output` destination, so design documents from earlier runs do not block a new run.
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

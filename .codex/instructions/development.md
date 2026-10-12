# Development Rules

Apply these rules when writing or modifying code.

## Tests and verification

- When the project has a test suite, use test-driven development for behavior
  changes that need automated coverage: add or update a meaningful failing test,
  implement the change, then refactor.
- Avoid tests that merely mirror the implementation or cover only reversible,
  low-impact wording changes. Verify prompt and documentation changes through
  their contracts, references, and repository consistency checks.
- If no test suite exists, manually verify the expected cases after implementation.
- After code changes, run the applicable tests and the checks required by
  [AGENTS.md](../../AGENTS.md). Confirm their results before marking the work
  complete; report checks that could not run and any remaining failures.

## Self-check and formatting

- Re-check completed code against [comment.md](comment.md). If AI-facing prompts
  also changed, re-check them against [prompt.md](prompt.md).
- Target a maximum code line length of about 100 characters.

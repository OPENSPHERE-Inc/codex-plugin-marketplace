# Comment Discipline

Apply these rules to code comments when writing or modifying code. Human-facing
documentation follows [document.md](document.md).

- Fix the code instead of adding multi-paragraph comments defending why it is
  acceptable.
- When the root-cause fix is out of scope, awaits a design decision, or is
  intentionally deferred, leave a short `FIXME:` or `TODO:` stating the problem
  and recommended fix direction in one or two lines.
- Use a longer comment only for a non-obvious invariant that cannot be inferred
  from the code. Keep it to one focused paragraph.
- Write for future readers of the codebase. Describe only invariants,
  constraints, and assumptions needed to understand the code. Avoid references
  to the current chat, user requests, prior implementations, or porting history.
  Keep change history in commit messages and PR descriptions.

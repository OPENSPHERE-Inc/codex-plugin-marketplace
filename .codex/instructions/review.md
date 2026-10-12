# Code Review Rules

Apply these rules when conducting code reviews.

- Prioritize real bugs, risks, and unclear code. Do not require comments to
  explain every technical subtlety.
- Raise a comment-related finding only when it actively misleads and could cause
  a maintainer to introduce a bug. Minor wording polish is Info at most and can
  usually be omitted.
- When a real problem is deferred because its root-cause fix is out of scope or
  awaits a design decision, recommend a short `FIXME:` or `TODO:` pointing to the
  problem and fix direction. Avoid lengthy justifications of the current code.
- Structural improvements, naming cleanups, and similar refactoring suggestions
  are Info at most unless they address a bug, syntax error, or coding convention
  violation.

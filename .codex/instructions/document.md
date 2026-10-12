# Documentation Discipline

Apply these rules to human-facing documentation, including README files, API
references, and design documents. AI-facing instructions in AGENTS.md,
`.codex/`, and plugin skills, templates, and rules follow [prompt.md](prompt.md).

## Audience and references

- Write for third-party readers who will consult the document later. State facts,
  specifications, and assumptions without relying on the current chat, prior
  versions, or porting history. Keep change history in commit messages and PR
  descriptions.
- Chat-dependent phrasing is allowed when explicitly requested by the user or
  when the document itself records that context, such as a plan, report, or
  meeting note.
- Cite only material readers can follow, such as a repository file, public URL,
  or published specification. Do not cite undocumented verbal decisions,
  private chat messages, or unpublished material. If no accessible reference
  exists, rewrite the passage to stand on its own without that citation.

## Markdown

- Escape a pipe inside inline code in a table cell as `\|`; code spans do not
  protect the character from being parsed as a table separator.
- Wrap source at sentence or clause boundaries, targeting at most 100 characters
  per line. Keep table rows, headings, and other syntax that requires a single
  line intact.
- A single source newline renders as whitespace within a paragraph. Use blank
  lines for separate paragraphs or lists for separate items. Use two trailing
  spaces or `<br>` sparingly when an in-paragraph line break is required.

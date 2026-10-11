# Prompt Discipline

Apply these rules when writing or modifying AI-facing instructions: AGENTS.md,
`.codex/agents/*.toml`, `.codex/instructions/*.md`, and plugin skills, task
templates, rules, and agent profiles in `plugins/` and `src/`. Human-facing
documentation follows [document.md](document.md).

## Goals and contracts

- State the concrete goal and available tools. Leave the method to the executing
  agent where consistency and reproducibility do not require a fixed procedure.
- Specify required inputs, branch conditions, failure handling, authorization
  boundaries, side effects, stop conditions, and output formats where they affect
  execution. Preserve exact command forms and return schemas when required.
- When strict command sequences are needed, consider extracting them into a
  script and stating its invocation and expected result. Avoid procedural command
  lists when a result contract is sufficient.

## Instructions and rationale

- Address the executing agent directly. Omit human-oriented introductions,
  creation history, and narration such as "The following describes ...".
- Keep background only when it affects a decision. Remove a sentence if removing
  it does not change the action the agent should take. When a sentence mixes
  instruction and redundant explanation, retain the instruction.
- Remove effect restatements such as "Read it. This obtains the data", redundant
  emphasis such as "without omission", and forward references that do not help
  execute the current step.
- Retain reasons that establish constraints, hidden premises, or edge-case
  decisions. For example, a boundary's failure mode may determine whether an
  apparently similar alternative is valid. Remove reasons that only restate an
  action's inherent effect.
- Put editing policies for prompts in this rule or another dedicated authoring
  rule. Keep them out of operational skill and task instructions unless editing
  those prompts is itself the assigned task.
- Make each prompt understandable without chat history. Avoid references such as
  "Because the user said ..." or "In the previous prompt ...". Supply required
  context through explicit inputs.

## Structure and output

- Keep heading levels, decoration, and emphasis minimal. Use blank lines between
  paragraphs; avoid line breaks added only for decoration.
- Prefer lists to tables, except when a table defines the requested output format.
- Include only context needed for the task. Remove digressions, repetition, and
  speculative precautions. Replace vague directives such as "appropriately"
  with decision criteria.
- In Markdown output specifications, use lists or blank-line-separated paragraphs
  for distinct items. A single source newline renders as whitespace, not a
  visible line break.

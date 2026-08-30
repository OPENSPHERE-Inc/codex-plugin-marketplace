#!/usr/bin/env python3
"""Validate the Codex marketplace, plugin manifests, and localized trees."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAMES = ("cprompt", "creview", "cdev")
PLUGIN_VERSIONS = {
    "cprompt": "0.1.0",
    "creview": "0.1.1",
    "cdev": "0.1.0",
}
MARKETPLACE_NAME = "opensphere-inc-codex"
UUID_PATTERN = re.compile(
    r"^template_id:\s*"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12})\s*$",
    re.MULTILINE | re.IGNORECASE,
)
LEGACY_PATTERNS = {
    "Claude plugin-root variable": re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}"),
    "Claude project directory": re.compile(r"\.claude(?:[/\\]|$)", re.IGNORECASE),
    "Claude plugin manifest": re.compile(r"\.claude-plugin", re.IGNORECASE),
    "Claude tool frontmatter": re.compile(r"^allowed-tools:", re.MULTILINE | re.IGNORECASE),
    "Claude background task option": re.compile(r"run_in_background", re.IGNORECASE),
    "Claude subagent selector": re.compile(r"subagent_type\s*=", re.IGNORECASE),
    "Claude SendMessage tool": re.compile(r"\bSendMessage\b", re.IGNORECASE),
    "Claude TodoWrite tool": re.compile(r"\bTodoWrite\b", re.IGNORECASE),
    "removed shell helper": re.compile(r"(?:fetch-diff|del-tmp)\.sh", re.IGNORECASE),
    "Claude slash command": re.compile(r"/(?:creview|cprompt|cdev):", re.IGNORECASE),
}


def load_json(path: Path, errors: list[str]) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {error}")
        return None


def runtime_files(root: Path) -> dict[Path, Path]:
    result: dict[Path, Path] = {}
    if not root.is_dir():
        return result
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.parts[0] == ".codex-plugin":
            continue
        if relative.as_posix() in {"README.md", "README_ja.md"}:
            continue
        result[relative] = path
    return result


def validate_marketplace(errors: list[str]) -> None:
    path = ROOT / ".agents" / "plugins" / "marketplace.json"
    data = load_json(path, errors)
    if not isinstance(data, dict):
        return
    if data.get("name") != MARKETPLACE_NAME:
        errors.append(f"{path.relative_to(ROOT)}: expected name {MARKETPLACE_NAME!r}")
    entries = data.get("plugins")
    if not isinstance(entries, list):
        errors.append(f"{path.relative_to(ROOT)}: plugins must be an array")
        return
    by_name = {
        entry.get("name"): entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
    if set(by_name) != set(PLUGIN_NAMES):
        errors.append(
            f"{path.relative_to(ROOT)}: expected plugins {list(PLUGIN_NAMES)}, "
            f"found {sorted(by_name)}"
        )
    for name in PLUGIN_NAMES:
        entry = by_name.get(name)
        if not entry:
            continue
        expected_source = {"source": "local", "path": f"./plugins/{name}"}
        if entry.get("source") != expected_source:
            errors.append(f"{path.relative_to(ROOT)}: invalid source for {name}")
        if entry.get("category") != "Developer Tools":
            errors.append(f"{path.relative_to(ROOT)}: invalid category for {name}")
        policy = entry.get("policy")
        if not isinstance(policy, dict) or policy.get("installation") != "AVAILABLE":
            errors.append(f"{path.relative_to(ROOT)}: {name} must be AVAILABLE")


def validate_manifest(name: str, errors: list[str]) -> None:
    path = ROOT / "plugins" / name / ".codex-plugin" / "plugin.json"
    data = load_json(path, errors)
    if not isinstance(data, dict):
        return
    expected = {
        "name": name,
        "version": PLUGIN_VERSIONS[name],
        "skills": "./skills/",
        "license": "MIT",
    }
    for key, value in expected.items():
        if data.get(key) != value:
            errors.append(
                f"{path.relative_to(ROOT)}: expected {key}={value!r}, "
                f"found {data.get(key)!r}"
            )
    interface = data.get("interface")
    if not isinstance(interface, dict) or not interface.get("defaultPrompt"):
        errors.append(f"{path.relative_to(ROOT)}: interface.defaultPrompt is required")


def frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    return text[4:end]


def validate_skills(root: Path, errors: list[str]) -> int:
    count = 0
    for path in sorted(root.glob("*/SKILL.md")):
        count += 1
        text = path.read_text(encoding="utf-8")
        block = frontmatter(text)
        if block is None:
            errors.append(f"{path.relative_to(ROOT)}: missing YAML frontmatter")
            continue
        name_match = re.search(r"^name:\s*(.+?)\s*$", block, re.MULTILINE)
        description_match = re.search(r"^description:\s*(.+?)\s*$", block, re.MULTILINE)
        expected_name = path.parent.name
        if not name_match or name_match.group(1).strip("\"'") != expected_name:
            errors.append(
                f"{path.relative_to(ROOT)}: frontmatter name must be {expected_name!r}"
            )
        if not description_match or not description_match.group(1).strip("\"'"):
            errors.append(f"{path.relative_to(ROOT)}: description is required")
        if re.search(r"^allowed-tools:", block, re.MULTILINE | re.IGNORECASE):
            errors.append(f"{path.relative_to(ROOT)}: allowed-tools is Claude-specific")
    return count


def validate_templates(
    label: str, files: dict[Path, Path], errors: list[str]
) -> dict[Path, str]:
    by_path: dict[Path, str] = {}
    owners: dict[str, Path] = {}
    for relative, path in files.items():
        if path.suffix.lower() != ".md":
            continue
        match = UUID_PATTERN.search(path.read_text(encoding="utf-8"))
        if not match:
            continue
        template_id = match.group(1).lower()
        by_path[relative] = template_id
        previous = owners.get(template_id)
        if previous:
            errors.append(
                f"{label}: duplicate template_id {template_id}: "
                f"{previous.as_posix()} and {relative.as_posix()}"
            )
        owners[template_id] = relative
    return by_path


def validate_python(errors: list[str]) -> int:
    count = 0
    for path in sorted(ROOT.rglob("*.py")):
        if ".git" in path.parts:
            continue
        count += 1
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            errors.append(f"{path.relative_to(ROOT)}: Python parse failed: {error}")
    return count


def validate_plugin(name: str, errors: list[str]) -> tuple[int, int]:
    validate_manifest(name, errors)
    active_root = ROOT / "plugins" / name
    source_root = ROOT / "src" / name
    active = runtime_files(active_root)
    source = runtime_files(source_root)
    if set(active) != set(source):
        active_only = sorted(path.as_posix() for path in set(active) - set(source))
        source_only = sorted(path.as_posix() for path in set(source) - set(active))
        if active_only:
            errors.append(f"{name}: active-only runtime files: {active_only}")
        if source_only:
            errors.append(f"{name}: source-only runtime files: {source_only}")

    active_ids = validate_templates(f"plugins/{name}", active, errors)
    source_ids = validate_templates(f"src/{name}", source, errors)
    if active_ids != source_ids:
        errors.append(f"{name}: template_id mapping differs between source and active trees")

    for relative in sorted(set(active) & set(source)):
        active_path = active[relative]
        source_path = source[relative]
        if relative.suffix.lower() == ".py":
            if active_path.read_bytes() != source_path.read_bytes():
                errors.append(
                    f"{name}: Python helper differs across localized trees: "
                    f"{relative.as_posix()}"
                )
        if relative.suffix.lower() not in {".md", ".py", ".json", ".toml"}:
            continue
        for tree_name, path in (("active", active_path), ("source", source_path)):
            text = path.read_text(encoding="utf-8")
            for legacy_name, pattern in LEGACY_PATTERNS.items():
                if pattern.search(text):
                    errors.append(
                        f"{name} {tree_name}/{relative.as_posix()}: "
                        f"contains {legacy_name}"
                    )

    skill_count = validate_skills(active_root / "skills", errors)
    validate_skills(source_root / "skills", errors)
    if skill_count == 0:
        errors.append(f"{name}: no skills found")
    for readme in ("README.md", "README_ja.md"):
        if not (active_root / readme).is_file():
            errors.append(f"plugins/{name}/{readme}: missing")
    return len(active), skill_count


def main() -> int:
    errors: list[str] = []
    validate_marketplace(errors)
    runtime_count = 0
    skill_count = 0
    for name in PLUGIN_NAMES:
        plugin_runtime, plugin_skills = validate_plugin(name, errors)
        runtime_count += plugin_runtime
        skill_count += plugin_skills
    python_count = validate_python(errors)

    if errors:
        print(f"Validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "Validation passed: "
        f"{len(PLUGIN_NAMES)} plugins, {skill_count} skills, "
        f"{runtime_count} runtime files per language, {python_count} Python files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

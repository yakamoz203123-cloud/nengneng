"""Dependency-free structural validator for the life-model-writing Skill."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from eval_common import EvaluationDataError, load_case_sets


CORE_HEADINGS = frozenset(
    {
        "一句话定义",
        "它解释什么",
        "最小模型",
        "关键变量",
        "推演步骤",
        "适合解释的生活问题",
        "不适合解释的生活问题",
        "常见误用",
        "最小例子",
        "事实与证据边界",
        "可靠来源",
    }
)
SELECTION_HEADINGS = frozenset(
    {
        "候选理论评分",
        "排除条件",
        "可观察预测",
        "可联合理论",
        "连接变量",
    }
)

FRONTMATTER_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$")
MARKDOWN_LINK = re.compile(r"!??\[[^\]]*\]\(([^)]+)\)")
HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
NUMBERED_THEORY_CARD = re.compile(r"theory-(\d{2})-")
THEORY_ROUTE = re.compile(r"references/(theory-\d{2}-[^)\s`]+\.md)")
STANDALONE_MARKER = re.compile(r"^\s*(TODO|TBD|FIXME)\s*$", re.IGNORECASE)
CASE_SET_NAMES = ("evals.json", "real-cases.json", "activation-cases.json")
IGNORED_SCAN_DIRS = {"tests", "__pycache__", ".git"}


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_text(path: Path, root: Path, errors: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{_relative(path, root)}: cannot read file: {exc}")
    except UnicodeError as exc:
        errors.append(f"{_relative(path, root)}: invalid UTF-8: {exc}")
    return None


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the flat frontmatter fields used by this Skill."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        closing = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return {}

    fields: dict[str, str] = {}
    for line in lines[1:closing]:
        match = FRONTMATTER_LINE.match(line)
        if match:
            value = match.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            fields[match.group(1)] = value
    return fields


def _validate_frontmatter(skill_file: Path, root: Path, errors: list[str]) -> None:
    text = _read_text(skill_file, root, errors)
    if text is None:
        return
    if not text.startswith("---"):
        errors.append("SKILL.md: missing frontmatter")
        return
    fields = parse_frontmatter(text)
    name = fields.get("name", "")
    if not re.fullmatch(r"[a-z0-9-]+", name):
        errors.append("SKILL.md: invalid name")
    if not fields.get("description", "").strip():
        errors.append("SKILL.md: missing description")


def _validate_links(path: Path, root: Path, errors: list[str]) -> None:
    text = _read_text(path, root, errors)
    if text is None:
        return
    for target in MARKDOWN_LINK.findall(text):
        target = target.strip().strip("<>")
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        target = target.split("#", 1)[0].split("?", 1)[0]
        if not target:
            continue
        link_path = (path.parent / target).resolve()
        if not link_path.is_file():
            errors.append(f"{_relative(path, root)}: broken link {target}")


def _validate_theory_card(path: Path, root: Path, errors: list[str]) -> None:
    text = _read_text(path, root, errors)
    if text is None:
        return
    headings = set(HEADING.findall(text))
    required_headings = CORE_HEADINGS | SELECTION_HEADINGS
    card_match = NUMBERED_THEORY_CARD.search(path.name)
    card_number = int(card_match.group(1)) if card_match else None
    if card_number in {13, 14}:
        required_headings = required_headings | {"社会机制桥接"}
    for heading in sorted(required_headings - headings):
        errors.append(f"{_relative(path, root)}: missing theory heading {heading}")


def _validate_theory_card_inventory(
    card_paths: list[Path], root: Path, errors: list[str]
) -> None:
    numbers = {
        int(match.group(1))
        for path in card_paths
        if (match := NUMBERED_THEORY_CARD.search(path.name))
    }
    for number in sorted(set(range(1, 15)) - numbers):
        errors.append(
            f"references: missing theory card theory-{number:02d}-*.md"
        )


def _validate_theory_routes(
    skill_file: Path, card_paths: list[Path], root: Path, errors: list[str]
) -> None:
    text = _read_text(skill_file, root, errors)
    if text is None:
        return

    routed_names = set(THEORY_ROUTE.findall(text))
    for path in card_paths:
        if path.name not in routed_names:
            errors.append(f"SKILL.md: missing theory route {path.name}")


def _validate_case_files(root: Path, errors: list[str]) -> None:
    eval_dir = root / "evals"
    for name in CASE_SET_NAMES:
        path = eval_dir / name
        if not path.exists():
            continue
        try:
            load_case_sets([path])
        except EvaluationDataError as exc:
            errors.append(f"{_relative(path, root)}: {exc}")


def _validate_markers(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or any(part in IGNORED_SCAN_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in {".md", ".json", ".yaml", ".yml"}:
            continue
        text = _read_text(path, root, errors)
        if text is None:
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            if STANDALONE_MARKER.match(line):
                errors.append(
                    f"{_relative(path, root)}:{line_number}: unfinished scaffold marker"
                )


def validate_skill_root(skill_root: Path) -> list[str]:
    """Return stable structural errors for one Skill directory."""

    root = skill_root.resolve()
    errors: list[str] = []
    skill_file = root / "SKILL.md"
    if not skill_file.is_file():
        errors.append("SKILL.md: file is missing")
        return errors

    _validate_frontmatter(skill_file, root, errors)
    for path in root.rglob("*.md"):
        if any(part in IGNORED_SCAN_DIRS for part in path.parts):
            continue
        _validate_links(path, root, errors)

    references = root / "references"
    card_paths = sorted(references.glob("theory-[0-9][0-9]-*.md"))
    _validate_theory_card_inventory(card_paths, root, errors)
    _validate_theory_routes(skill_file, card_paths, root, errors)
    for path in card_paths:
        _validate_theory_card(path, root, errors)

    _validate_case_files(root, errors)
    _validate_markers(root, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_root", type=Path)
    args = parser.parse_args(argv)

    try:
        errors = validate_skill_root(args.skill_root)
    except OSError as exc:
        print(f"VALIDATION=ERROR {exc}", file=sys.stderr)
        return 2

    if errors:
        print("VALIDATION=FAIL")
        print("\n".join(errors))
        return 1
    print("VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

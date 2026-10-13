"""Resolve a declared, auditable reference bundle for an evaluation case."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ReferenceRouteError(ValueError):
    """Raised when a reference route is missing, invalid, or unsafe."""


def _relative_file(root: Path, value: object, source: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ReferenceRouteError(f"{source} must be a non-empty relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ReferenceRouteError(f"{source} must stay inside the Skill root")
    resolved = (root / relative).resolve()
    root_resolved = root.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ReferenceRouteError(f"{source} escapes the Skill root")
    if not resolved.is_file():
        raise ReferenceRouteError(f"{source} does not exist: {value}")
    return relative


def load_routes(route_path: Path, skill_root: Path) -> dict[str, object]:
    route_path = Path(route_path)
    skill_root = Path(skill_root)
    try:
        data = json.loads(route_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReferenceRouteError(f"cannot read routes: {route_path}") from exc
    if not isinstance(data, dict):
        raise ReferenceRouteError("routes must be an object")

    raw_common = data.get("common")
    if not isinstance(raw_common, list):
        raise ReferenceRouteError("routes.common must be a list")
    common = [
        _relative_file(skill_root, value, f"routes.common[{index}]").as_posix()
        for index, value in enumerate(raw_common)
    ]

    raw_cases = data.get("cases")
    if not isinstance(raw_cases, dict) or not raw_cases:
        raise ReferenceRouteError("routes.cases must be a non-empty object")
    cases: dict[str, list[str]] = {}
    for pair_id, raw_files in raw_cases.items():
        if not isinstance(pair_id, str) or not pair_id.strip():
            raise ReferenceRouteError("route case ids must be non-empty strings")
        if not isinstance(raw_files, list):
            raise ReferenceRouteError(f"routes.cases.{pair_id} must be a list")
        cases[pair_id] = [
            _relative_file(skill_root, value, f"routes.cases.{pair_id}[{index}]").as_posix()
            for index, value in enumerate(raw_files)
        ]
    return {"common": common, "cases": cases}


def build_skill_context(
    skill_root: Path, routes: dict[str, object], pair_id: str
) -> tuple[str, list[str]]:
    skill_root = Path(skill_root)
    skill_path = skill_root / "SKILL.md"
    if not skill_path.is_file():
        raise ReferenceRouteError(f"missing Skill entrypoint: {skill_path}")
    cases = routes.get("cases")
    common = routes.get("common")
    if not isinstance(cases, dict) or pair_id not in cases:
        raise ReferenceRouteError(f"no reference route declared for pair: {pair_id}")
    if not isinstance(common, list) or not all(isinstance(item, str) for item in common):
        raise ReferenceRouteError("loaded routes.common is invalid")
    selected = list(common) + list(cases[pair_id])
    unique_files: list[str] = []
    for relative in selected:
        if relative not in unique_files:
            _relative_file(skill_root, relative, "loaded reference")
            unique_files.append(relative)

    chunks = ["# life-model-writing/SKILL.md\n\n" + skill_path.read_text(encoding="utf-8")]
    for relative in unique_files:
        chunks.append(
            f"\n\n--- REFERENCE: {relative} ---\n\n"
            + (skill_root / relative).read_text(encoding="utf-8")
        )
    return "".join(chunks), unique_files

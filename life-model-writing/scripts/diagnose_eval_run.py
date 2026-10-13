"""Aggregate independent reviewer error tags for a paired evaluation run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eval_common import normalize_case_id, read_json


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_taxonomy(path: Path) -> tuple[set[str], set[str]]:
    data = read_json(Path(path))
    raw_tags = data.get("tags")
    if not isinstance(raw_tags, list) or not raw_tags:
        raise ValueError("taxonomy.tags must be a non-empty list")
    tags: set[str] = set()
    for index, item in enumerate(raw_tags):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError(f"taxonomy.tags[{index}].id must be a string")
        tag_id = item["id"].strip()
        if not tag_id or tag_id in tags:
            raise ValueError(f"taxonomy.tags[{index}].id must be unique and non-empty")
        tags.add(tag_id)

    raw_blocking = data.get("blocking_tags", [])
    if not isinstance(raw_blocking, list) or any(not isinstance(tag, str) for tag in raw_blocking):
        raise ValueError("taxonomy.blocking_tags must be a list of strings")
    blocking = set(raw_blocking)
    unknown_blocking = blocking - tags
    if unknown_blocking:
        raise ValueError("taxonomy.blocking_tags contains unknown tags")
    return tags, blocking


def _manifest_case_ids(manifest: dict[str, object]) -> set[str]:
    raw_cases = manifest.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("manifest.cases must be a non-empty list")
    case_ids: set[str] = set()
    for index, item in enumerate(raw_cases):
        if not isinstance(item, dict):
            raise ValueError(f"manifest.cases[{index}] must be an object")
        try:
            case_id = normalize_case_id(item.get("id"))  # type: ignore[arg-type]
        except ValueError as exc:
            raise ValueError(f"manifest.cases[{index}].id: {exc}") from exc
        if case_id in case_ids:
            raise ValueError(f"manifest contains duplicate case id: {case_id}")
        case_ids.add(case_id)
    return case_ids


def _load_reveal(run_dir: Path, case_ids: set[str]) -> dict[str, str]:
    reveal = read_json(run_dir / "reveal.json")
    raw_pairs = reveal.get("pairs")
    if not isinstance(raw_pairs, list) or not raw_pairs:
        raise ValueError("reveal.pairs must be a non-empty list")

    conditions: dict[str, str] = {}
    pair_ids: set[str] = set()
    for index, pair in enumerate(raw_pairs):
        if not isinstance(pair, dict):
            raise ValueError(f"reveal.pairs[{index}] must be an object")
        pair_id = pair.get("pair_id")
        if not isinstance(pair_id, str) or not pair_id.strip() or pair_id in pair_ids:
            raise ValueError(f"reveal.pairs[{index}].pair_id must be unique")
        pair_ids.add(pair_id)
        for field, condition in (("skill_case_id", "skill"), ("ordinary_case_id", "ordinary")):
            try:
                case_id = normalize_case_id(pair.get(field))  # type: ignore[arg-type]
            except ValueError as exc:
                raise ValueError(f"reveal.pairs[{index}].{field}: {exc}") from exc
            if case_id not in case_ids:
                raise ValueError(f"reveal references unknown case: {case_id}")
            if case_id in conditions:
                raise ValueError(f"reveal assigns case more than once: {case_id}")
            conditions[case_id] = condition

    if set(conditions) != case_ids:
        missing = sorted(case_ids - set(conditions))
        raise ValueError(f"reveal does not map all manifest cases: {missing}")
    return conditions


def _validate_diagnostic(
    path: Path, case_id: str, allowed_tags: set[str]
) -> tuple[bool, list[str]]:
    data = read_json(path)
    if data.get("case_id") != case_id:
        raise ValueError("diagnostic.case_id does not match filename")
    evaluator = data.get("evaluator")
    if not isinstance(evaluator, dict) or not isinstance(evaluator.get("independent"), bool):
        raise ValueError("diagnostic.evaluator.independent must be a boolean")
    raw_tags = data.get("error_tags", [])
    if not isinstance(raw_tags, list) or any(not isinstance(tag, str) for tag in raw_tags):
        raise ValueError("diagnostic.error_tags must be a list of strings")
    tags = [tag.strip() for tag in raw_tags]
    if any(not tag for tag in tags) or len(set(tags)) != len(tags):
        raise ValueError("diagnostic.error_tags must contain unique non-empty strings")
    unknown = sorted(set(tags) - allowed_tags)
    if unknown:
        raise ValueError(f"unknown diagnostic tags: {', '.join(unknown)}")
    return bool(evaluator["independent"]), tags


def _empty_condition() -> dict[str, object]:
    return {
        "case_count": 0,
        "verified_case_count": 0,
        "error_case_count": 0,
        "tag_counts": {},
        "error_case_rate": None,
    }


def diagnose_run(run_dir: Path, taxonomy_path: Path) -> dict[str, object]:
    """Validate and aggregate independent error tags for one paired run."""

    run_dir = Path(run_dir)
    blocking_reasons: list[str] = []
    unverified_reasons: list[str] = []
    conditions: dict[str, dict[str, object]] = {
        "skill": _empty_condition(),
        "ordinary": _empty_condition(),
    }

    try:
        manifest = read_json(run_dir / "manifest.json")
        case_ids = _manifest_case_ids(manifest)
    except (OSError, ValueError) as exc:
        blocking_reasons.append(f"invalid-run:{exc}")
        result: dict[str, object] = {
            "run_id": None,
            "status": "fail",
            "verified_case_count": 0,
            "blocking_reasons": blocking_reasons,
            "unverified_reasons": unverified_reasons,
            "conditions": conditions,
        }
        _write_json(run_dir / "diagnostics-summary.json", result)
        return result

    try:
        condition_by_case = _load_reveal(run_dir, case_ids)
    except (OSError, ValueError) as exc:
        blocking_reasons.append(f"invalid-reveal:{exc}")
        result = {
            "run_id": manifest.get("run_id"),
            "status": "fail",
            "verified_case_count": 0,
            "blocking_reasons": blocking_reasons,
            "unverified_reasons": unverified_reasons,
            "conditions": conditions,
        }
        _write_json(run_dir / "diagnostics-summary.json", result)
        return result

    try:
        allowed_tags, blocking_tags = _load_taxonomy(Path(taxonomy_path))
    except (OSError, ValueError) as exc:
        blocking_reasons.append(f"invalid-taxonomy:{exc}")
        result = {
            "run_id": manifest.get("run_id"),
            "status": "fail",
            "verified_case_count": 0,
            "blocking_reasons": blocking_reasons,
            "unverified_reasons": unverified_reasons,
            "conditions": conditions,
        }
        _write_json(run_dir / "diagnostics-summary.json", result)
        return result

    for condition_name, condition in conditions.items():
        condition["case_count"] = sum(
            value == condition_name for value in condition_by_case.values()
        )

    diagnostics_dir = run_dir / "diagnostics"
    for case_id in sorted(case_ids):
        condition_name = condition_by_case[case_id]
        diagnostic_path = diagnostics_dir / f"{case_id}.json"
        if not diagnostic_path.is_file():
            unverified_reasons.append(f"missing-diagnostic:{case_id}")
            continue
        try:
            independent, tags = _validate_diagnostic(diagnostic_path, case_id, allowed_tags)
        except (OSError, ValueError) as exc:
            message = str(exc)
            if message.startswith("unknown diagnostic tags: "):
                for tag in message.removeprefix("unknown diagnostic tags: ").split(", "):
                    blocking_reasons.append(f"unknown-tag:{case_id}:{tag}")
            else:
                blocking_reasons.append(f"invalid-diagnostic:{case_id}:{message}")
            continue
        if not independent:
            unverified_reasons.append(f"unverified-diagnostic:{case_id}")
            continue

        condition = conditions[condition_name]
        condition["verified_case_count"] = int(condition["verified_case_count"]) + 1
        if tags:
            condition["error_case_count"] = int(condition["error_case_count"]) + 1
        tag_counts = condition["tag_counts"]
        if not isinstance(tag_counts, dict):
            raise ValueError("internal error: tag_counts must be an object")
        for tag in tags:
            tag_counts[tag] = int(tag_counts.get(tag, 0)) + 1
            if tag in blocking_tags:
                blocking_reasons.append(f"blocking-tag:{case_id}:{tag}")

    for condition in conditions.values():
        verified = int(condition["verified_case_count"])
        condition["error_case_rate"] = (
            int(condition["error_case_count"]) / verified if verified else None
        )

    status = "fail" if blocking_reasons else "unverified" if unverified_reasons else "pass"
    result = {
        "run_id": manifest.get("run_id"),
        "status": status,
        "verified_case_count": sum(
            int(condition["verified_case_count"]) for condition in conditions.values()
        ),
        "blocking_reasons": sorted(set(blocking_reasons)),
        "unverified_reasons": sorted(set(unverified_reasons)),
        "conditions": conditions,
    }
    _write_json(run_dir / "diagnostics-summary.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--taxonomy", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        result = diagnose_run(args.run_dir, args.taxonomy)
    except (OSError, ValueError) as exc:
        print(f"V05_DIAGNOSTICS=ERROR {exc}")
        return 1

    print(
        "V05_DIAGNOSTICS=SUMMARY "
        f"status={result['status']} "
        f"verified={result['verified_case_count']}"
    )
    return {"pass": 0, "fail": 1, "unverified": 2}[str(result["status"])]


if __name__ == "__main__":
    raise SystemExit(main())

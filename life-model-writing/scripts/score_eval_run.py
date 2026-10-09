"""Run deterministic output checks and aggregate independent rubric scores."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from eval_common import read_json


LENGTH_BOUNDS = {
    "short": (400, 600),
    "standard": (800, 1200),
    "long": (1500, 2200),
}
ABSOLUTE_LANGUAGE = re.compile(r"所有人|总是|必然|一定|注定")
BOUNDARY_LANGUAGE = re.compile(r"但|不过|取决于|不一定|可能|条件")
MULTIPLE_VERSION = re.compile(r"(?:^|\n)\s*(?:版本|方案)\s*[一二三四五12345A-C]")


def count_non_whitespace_characters(text: str) -> int:
    return sum(not character.isspace() for character in text)


def _json_write(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def check_output(case: dict[str, object], output_path: Path) -> dict[str, object]:
    """Check observable output invariants without judging content quality."""

    if not output_path.is_file():
        return {
            "case_id": str(case.get("id", "unknown")),
            "status": "unverified",
            "checks": [{"name": "output-exists", "status": "unverified"}],
            "review_flags": ["missing-output"],
        }

    try:
        text = output_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {
            "case_id": str(case.get("id", "unknown")),
            "status": "fail",
            "checks": [{"name": "output-readable", "status": "fail", "detail": str(exc)}],
            "review_flags": [],
        }

    checks: list[dict[str, object]] = [
        {"name": "output-exists", "status": "pass"},
        {
            "name": "output-non-empty",
            "status": "pass" if text.strip() else "fail",
        },
    ]
    contract = case.get("length_contract")
    if contract in LENGTH_BOUNDS:
        character_count = count_non_whitespace_characters(text)
        lower, upper = LENGTH_BOUNDS[str(contract)]
        checks.append(
            {
                "name": "length-contract",
                "status": "pass" if lower <= character_count <= upper else "fail",
                "character_count": character_count,
                "lower": lower,
                "upper": upper,
            }
        )
    else:
        checks.append({"name": "length-contract", "status": "review"})

    review_flags: list[str] = []
    if ABSOLUTE_LANGUAGE.search(text):
        review_flags.append("absolute-language")
    if not BOUNDARY_LANGUAGE.search(text):
        review_flags.append("boundary-language")
    if MULTIPLE_VERSION.search(text):
        review_flags.append("multiple-version")

    mandatory_statuses = [check["status"] for check in checks if check["status"] != "review"]
    if "fail" in mandatory_statuses:
        status = "fail"
    elif review_flags:
        status = "review"
    else:
        status = "pass"
    return {
        "case_id": str(case.get("id", "unknown")),
        "status": status,
        "checks": checks,
        "review_flags": review_flags,
    }


def _dimension_ids(rubric: dict[str, object]) -> list[str]:
    dimensions = rubric.get("dimensions")
    if not isinstance(dimensions, list):
        raise ValueError("rubric.dimensions must be a list")
    ids: list[str] = []
    for index, dimension in enumerate(dimensions):
        if not isinstance(dimension, dict) or not isinstance(dimension.get("id"), str):
            raise ValueError(f"rubric.dimensions[{index}].id must be a string")
        ids.append(dimension["id"])
    return ids


def validate_score(
    score: dict[str, object], rubric: dict[str, object], case_id: str
) -> dict[str, object]:
    """Validate one evaluator score and derive its release status."""

    if score.get("case_id") != case_id:
        raise ValueError("score.case_id does not match the requested case")
    evaluator = score.get("evaluator")
    if not isinstance(evaluator, dict) or not isinstance(evaluator.get("independent"), bool):
        raise ValueError("score.evaluator.independent must be a boolean")

    dimension_ids = _dimension_ids(rubric)
    scores = score.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(dimension_ids):
        raise ValueError("score.scores must contain exactly the rubric dimensions")
    for dimension_id in dimension_ids:
        value = scores[dimension_id]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
            raise ValueError(f"score.scores.{dimension_id} must be an integer from 0 to 5")

    critical_errors = score.get("critical_errors", [])
    if not isinstance(critical_errors, list) or any(not isinstance(error, str) for error in critical_errors):
        raise ValueError("score.critical_errors must be a list of strings")
    allowed_errors = set(rubric["pass"]["critical_errors"])
    if any(error not in allowed_errors for error in critical_errors):
        raise ValueError("score contains an unknown critical error")

    total = sum(scores.values())
    if "total" in score and score["total"] != total:
        raise ValueError("score.total does not equal the dimension sum")

    pass_rules = rubric.get("pass")
    if not isinstance(pass_rules, dict):
        raise ValueError("rubric.pass must be an object")
    critical_dimensions = pass_rules.get("critical_dimensions", [])
    critical_floor = pass_rules.get("critical_floor")
    min_total = pass_rules.get("min_total")
    if not isinstance(critical_dimensions, list) or not isinstance(critical_floor, int) or not isinstance(min_total, int):
        raise ValueError("rubric.pass thresholds are invalid")

    if not evaluator["independent"]:
        status = "unverified"
    elif critical_errors:
        status = "fail"
    elif total < min_total:
        status = "fail"
    elif any(scores[dimension_id] < critical_floor for dimension_id in critical_dimensions):
        status = "fail"
    else:
        status = "pass"

    return {
        "case_id": case_id,
        "evaluator": evaluator,
        "scores": dict(scores),
        "critical_errors": list(critical_errors),
        "total": total,
        "status": status,
    }


def _score_status(run_dir: Path, case: dict[str, object], rubric: dict[str, object]) -> dict[str, object]:
    case_id = str(case["id"])
    score_path = run_dir / "scores" / f"{case_id}.json"
    if not score_path.is_file():
        return {"case_id": case_id, "score_status": "unverified", "score_error": "missing-score"}
    try:
        score = read_json(score_path)
        normalized = validate_score(score, rubric, case_id)
    except (ValueError, OSError) as exc:
        return {"case_id": case_id, "score_status": "unverified", "score_error": str(exc)}
    return {
        "case_id": case_id,
        "score_status": normalized["status"],
        "total": normalized["total"],
        "critical_errors": normalized["critical_errors"],
    }


def summarize_run(run_dir: Path, rubric_path: Path) -> dict[str, object]:
    """Write checks and an aggregate summary without rewriting raw outputs/scores."""

    run_dir = Path(run_dir)
    manifest = read_json(run_dir / "manifest.json")
    rubric = read_json(Path(rubric_path))
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise ValueError("manifest.cases must be a list")

    checks_dir = run_dir / "checks"
    checks_dir.mkdir(exist_ok=True)
    summary_cases: list[dict[str, object]] = []
    for case in cases:
        if not isinstance(case, dict) or "id" not in case:
            raise ValueError("manifest contains an invalid case")
        case_id = str(case["id"])
        check = check_output(case, run_dir / "outputs" / f"{case_id}.md")
        _json_write(checks_dir / f"{case_id}.json", check)
        score = _score_status(run_dir, case, rubric)
        summary_cases.append({**check, **score})

    counts = {"pass": 0, "fail": 0, "unverified": 0, "skipped": 0}
    verified_totals: list[int] = []
    for case in summary_cases:
        status = str(case["score_status"])
        if status not in counts:
            raise ValueError(f"unknown score status: {status}")
        counts[status] += 1
        if status in {"pass", "fail"} and isinstance(case.get("total"), int):
            verified_totals.append(case["total"])

    summary: dict[str, object] = {
        "run_id": manifest.get("run_id"),
        "counts": counts,
        "verified_case_count": len(verified_totals),
        "average_total": (
            sum(verified_totals) / len(verified_totals) if verified_totals else None
        ),
        "cases": summary_cases,
    }
    _json_write(run_dir / "summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--rubric", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        summary = summarize_run(args.run_dir, args.rubric)
    except (OSError, ValueError) as exc:
        print(f"EVALUATION_SCORE=ERROR {exc}")
        return 1
    print(
        "EVALUATION_SCORE=SUMMARY "
        f"pass={summary['counts']['pass']} "
        f"fail={summary['counts']['fail']} "
        f"unverified={summary['counts']['unverified']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

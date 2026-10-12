"""Run the v0.3 paired blind-test regression gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from score_eval_run import validate_score


REQUIRED_GATE_KEYS = {
    "min_skill_case_total",
    "min_skill_average_total",
    "min_skill_advantage",
    "min_skill_wins",
    "min_skill_dimension_average",
    "max_critical_errors",
}
CRITICAL_ERROR_SCOPES = {"all_cases", "skill_cases_only"}


def read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _case_ids(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{field} must be a non-empty list of strings")
    ids = [str(item) for item in value]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{field} contains duplicate case ids")
    return ids


def validate_contract(contract: dict[str, object]) -> None:
    """Validate the static contract used by all v0.3 regression runs."""

    case_ids = _case_ids(contract.get("case_ids"), "case_ids")
    pairs = contract.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("pairs must be a non-empty list")
    covered: set[str] = set()
    pair_ids: set[str] = set()
    for index, pair in enumerate(pairs):
        if not isinstance(pair, dict):
            raise ValueError(f"pairs[{index}] must be an object")
        pair_id = pair.get("pair_id")
        if not isinstance(pair_id, str) or not pair_id.strip() or pair_id in pair_ids:
            raise ValueError(f"pairs[{index}].pair_id must be unique")
        pair_ids.add(pair_id)
        ids = _case_ids(pair.get("case_ids"), f"pairs[{index}].case_ids")
        if len(ids) != 2:
            raise ValueError(f"pairs[{index}].case_ids must contain exactly two ids")
        covered.update(ids)
    if covered != set(case_ids):
        raise ValueError("pairs do not cover exactly the declared case_ids")

    hard_checks = contract.get("hard_checks")
    if not isinstance(hard_checks, dict):
        raise ValueError("hard_checks must be an object")
    for key in ("min_non_whitespace", "max_non_whitespace"):
        value = hard_checks.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"hard_checks.{key} must be a non-negative integer")
    if hard_checks["min_non_whitespace"] > hard_checks["max_non_whitespace"]:
        raise ValueError("hard_checks length bounds are inverted")
    _case_ids(hard_checks.get("forbidden_terms"), "hard_checks.forbidden_terms")

    gates = contract.get("regression_gates")
    if not isinstance(gates, dict) or set(gates) != REQUIRED_GATE_KEYS:
        raise ValueError(
            "regression_gates must contain exactly "
            + ", ".join(sorted(REQUIRED_GATE_KEYS))
        )
    for key, value in gates.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"regression_gates.{key} must be numeric")
    scope = contract.get("critical_error_scope", "all_cases")
    if scope not in CRITICAL_ERROR_SCOPES:
        raise ValueError(
            "critical_error_scope must be one of: "
            + ", ".join(sorted(CRITICAL_ERROR_SCOPES))
        )


def count_non_whitespace(text: str) -> int:
    return sum(not character.isspace() for character in text)


def check_output(
    output_path: Path, min_length: int, max_length: int, forbidden_terms: list[str]
) -> dict[str, object]:
    """Check only reproducible output invariants, not subjective quality."""

    case_id = output_path.stem
    if not output_path.is_file():
        return {"case_id": case_id, "status": "fail", "reason": "missing-output"}
    try:
        text = output_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {"case_id": case_id, "status": "fail", "reason": f"unreadable:{exc}"}
    character_count = count_non_whitespace(text)
    matched_terms = [term for term in forbidden_terms if term in text]
    reasons: list[str] = []
    if not text.strip():
        reasons.append("empty-output")
    if not min_length <= character_count <= max_length:
        reasons.append("length-out-of-range")
    if matched_terms:
        reasons.append("internal-leakage")
    return {
        "case_id": case_id,
        "status": "fail" if reasons else "pass",
        "character_count": character_count,
        "lower": min_length,
        "upper": max_length,
        "matched_forbidden_terms": matched_terms,
        "reasons": reasons,
    }


def _validate_reveal(
    run_dir: Path, contract: dict[str, object]
) -> tuple[dict[str, tuple[str, str]], list[str]]:
    reveal = read_json(run_dir / "reveal.json")
    raw_pairs = reveal.get("pairs")
    if not isinstance(raw_pairs, list):
        raise ValueError("reveal.pairs must be a list")
    expected_pairs = contract["pairs"]
    if not isinstance(expected_pairs, list):
        raise ValueError("contract.pairs must be a list")
    expected_by_id = {
        str(pair["pair_id"]): [str(item) for item in pair["case_ids"]]
        for pair in expected_pairs
        if isinstance(pair, dict)
    }
    mapping: dict[str, tuple[str, str]] = {}
    seen_cases: set[str] = set()
    for pair in raw_pairs:
        if not isinstance(pair, dict):
            raise ValueError("reveal pair must be an object")
        pair_id = pair.get("pair_id")
        skill_case_id = pair.get("skill_case_id")
        ordinary_case_id = pair.get("ordinary_case_id")
        if not all(isinstance(item, str) for item in (pair_id, skill_case_id, ordinary_case_id)):
            raise ValueError("reveal pair ids must be strings")
        if pair_id not in expected_by_id:
            raise ValueError(f"unknown reveal pair: {pair_id}")
        if {skill_case_id, ordinary_case_id} != set(expected_by_id[pair_id]):
            raise ValueError(f"reveal pair does not match contract: {pair_id}")
        if pair_id in mapping or skill_case_id in seen_cases or ordinary_case_id in seen_cases:
            raise ValueError(f"duplicate reveal mapping: {pair_id}")
        mapping[pair_id] = (skill_case_id, ordinary_case_id)
        seen_cases.update((skill_case_id, ordinary_case_id))
    if set(mapping) != set(expected_by_id):
        raise ValueError("reveal does not cover all contract pairs")
    return mapping, []


def _score_records(
    run_dir: Path,
    case_ids: list[str],
    rubric: dict[str, object],
) -> tuple[dict[str, dict[str, object]], list[str], list[str]]:
    records: dict[str, dict[str, object]] = {}
    unverified: list[str] = []
    failed: list[str] = []
    for case_id in case_ids:
        score_path = run_dir / "scores" / f"{case_id}.json"
        if not score_path.is_file():
            unverified.append(f"missing-score:{case_id}")
            continue
        try:
            score = read_json(score_path)
            normalized = validate_score(score, rubric, case_id)
        except (OSError, ValueError) as exc:
            unverified.append(f"invalid-score:{case_id}:{exc}")
            continue
        if normalized["status"] == "unverified":
            unverified.append(f"unverified-score:{case_id}")
            continue
        records[case_id] = normalized
        # A low comparative score is an observed result, not an invalid run.
        # The v0.3 gates evaluate the Skill condition's floor and paired delta;
        # only a declared critical error should block the run here.
        if normalized["critical_errors"]:
            failed.append(f"critical-error:{case_id}")
    return records, unverified, failed


def _mean(values: list[float | int]) -> float | None:
    return sum(values) / len(values) if values else None


def evaluate_run(
    run_dir: Path,
    contract_path: Path,
    rubric_path: Path | None = None,
) -> dict[str, object]:
    """Evaluate one v0.3 run and return a JSON-serializable gate report."""

    run_dir = Path(run_dir)
    contract = read_json(Path(contract_path))
    validate_contract(contract)
    rubric = read_json(
        rubric_path or Path(__file__).resolve().parents[1] / "evals" / "rubric.json"
    )
    case_ids = _case_ids(contract["case_ids"], "case_ids")
    manifest = read_json(run_dir / "manifest.json")
    manifest_case_ids = [
        str(case["id"])
        for case in manifest.get("cases", [])
        if isinstance(case, dict) and "id" in case
    ]
    blocking_reasons: list[str] = []
    if manifest_case_ids != case_ids:
        blocking_reasons.append("manifest-case-set-mismatch")

    hard_checks = contract["hard_checks"]
    assert isinstance(hard_checks, dict)
    min_length = int(hard_checks["min_non_whitespace"])
    max_length = int(hard_checks["max_non_whitespace"])
    forbidden_terms = [str(term) for term in hard_checks["forbidden_terms"]]
    checks = [
        check_output(
            run_dir / "outputs" / f"{case_id}.md",
            min_length,
            max_length,
            forbidden_terms,
        )
        for case_id in case_ids
    ]
    failed_checks = [check for check in checks if check["status"] == "fail"]
    if failed_checks:
        blocking_reasons.extend(
            f"output-check:{check['case_id']}:{','.join(check.get('reasons', []))}"
            for check in failed_checks
        )

    expected_output_names = {f"{case_id}.md" for case_id in case_ids}
    actual_output_names = {
        path.name for path in (run_dir / "outputs").glob("*.md")
    } if (run_dir / "outputs").is_dir() else set()
    extras = sorted(actual_output_names - expected_output_names)
    if extras:
        blocking_reasons.append("unexpected-output:" + ",".join(extras))

    try:
        reveal, _ = _validate_reveal(run_dir, contract)
    except (OSError, ValueError) as exc:
        reveal = {}
        blocking_reasons.append(f"invalid-reveal:{exc}")

    records, unverified_reasons, failed_scores = _score_records(run_dir, case_ids, rubric)
    expected_score_names = {f"{case_id}.json" for case_id in case_ids}
    actual_score_names = {
        path.name for path in (run_dir / "scores").glob("*.json")
    } if (run_dir / "scores").is_dir() else set()
    extra_scores = sorted(actual_score_names - expected_score_names)
    if extra_scores:
        blocking_reasons.append("unexpected-score:" + ",".join(extra_scores))

    critical_error_scope = str(contract.get("critical_error_scope", "all_cases"))
    if critical_error_scope == "all_cases":
        blocking_reasons.extend(failed_scores)
    elif reveal:
        skill_case_ids = {skill_id for skill_id, _ in reveal.values()}
        blocking_reasons.extend(
            reason
            for reason in failed_scores
            if reason.split(":", 1)[-1] in skill_case_ids
        )
    else:
        blocking_reasons.append("critical-error-scope-unavailable")

    skill_case_ids = {skill_id for skill_id, _ in reveal.values()} if reveal else set()
    ordinary_case_ids = {ordinary_id for _, ordinary_id in reveal.values()} if reveal else set()
    skill_critical_error_count = sum(
        len(records[case_id].get("critical_errors", []))
        for case_id in skill_case_ids
        if case_id in records
    )
    ordinary_critical_error_count = sum(
        len(records[case_id].get("critical_errors", []))
        for case_id in ordinary_case_ids
        if case_id in records
    )
    critical_error_count = sum(
        len(record.get("critical_errors", [])) for record in records.values()
    )

    metrics: dict[str, object] = {
        "skill_average_total": None,
        "ordinary_average_total": None,
        "skill_advantage": None,
        "skill_wins": 0,
        "ordinary_wins": 0,
        "ties": 0,
        "skill_dimension_averages": {},
        "critical_error_count": critical_error_count,
        "skill_critical_error_count": skill_critical_error_count,
        "ordinary_critical_error_count": ordinary_critical_error_count,
        "critical_error_scope": critical_error_scope,
    }
    if reveal:
        skill_records = [records[skill_id] for skill_id, _ in reveal.values() if skill_id in records]
        ordinary_records = [records[ordinary_id] for _, ordinary_id in reveal.values() if ordinary_id in records]
        if len(skill_records) == len(reveal) and len(ordinary_records) == len(reveal):
            skill_totals = [int(record["total"]) for record in skill_records]
            ordinary_totals = [int(record["total"]) for record in ordinary_records]
            skill_average = _mean(skill_totals)
            ordinary_average = _mean(ordinary_totals)
            assert skill_average is not None and ordinary_average is not None
            skill_wins = sum(skill > ordinary for skill, ordinary in zip(skill_totals, ordinary_totals))
            ordinary_wins = sum(skill < ordinary for skill, ordinary in zip(skill_totals, ordinary_totals))
            metrics.update(
                {
                    "skill_average_total": skill_average,
                    "ordinary_average_total": ordinary_average,
                    "skill_advantage": round(skill_average - ordinary_average, 2),
                    "skill_wins": skill_wins,
                    "ordinary_wins": ordinary_wins,
                    "ties": len(reveal) - skill_wins - ordinary_wins,
                    "skill_dimension_averages": {
                        dimension_id: _mean(
                            [int(record["scores"][dimension_id]) for record in skill_records]
                        )
                        for dimension_id in skill_records[0]["scores"]
                    },
                }
            )
        else:
            unverified_reasons.append("incomplete-paired-scores")

    gates = contract["regression_gates"]
    assert isinstance(gates, dict)
    gate_results: dict[str, object] = {}
    if records and reveal and metrics["skill_average_total"] is not None:
        skill_records = [records[skill_id] for skill_id, _ in reveal.values()]
        skill_totals = [int(record["total"]) for record in skill_records]
        dimension_averages = metrics["skill_dimension_averages"]
        assert isinstance(dimension_averages, dict)
        gate_results = {
            "min_skill_case_total": min(skill_totals) >= float(gates["min_skill_case_total"]),
            "min_skill_average_total": float(metrics["skill_average_total"]) >= float(gates["min_skill_average_total"]),
            "min_skill_advantage": float(metrics["skill_advantage"]) >= float(gates["min_skill_advantage"]),
            "min_skill_wins": int(metrics["skill_wins"]) >= int(gates["min_skill_wins"]),
            "min_skill_dimension_average": all(
                float(value) >= float(gates["min_skill_dimension_average"])
                for value in dimension_averages.values()
            ),
            "max_critical_errors": int(
                metrics[
                    "skill_critical_error_count"
                    if critical_error_scope == "skill_cases_only"
                    else "critical_error_count"
                ]
            ) <= int(gates["max_critical_errors"]),
        }
        for name, passed in gate_results.items():
            if not passed:
                blocking_reasons.append(f"gate-failed:{name}")
    else:
        unverified_reasons.append("metrics-unavailable")

    critical_error_blocked = any(
        reason.startswith("critical-error:") for reason in blocking_reasons
    )
    if failed_checks or critical_error_blocked or any(
        reason.startswith("gate-failed") for reason in blocking_reasons
    ):
        status = "fail"
    elif blocking_reasons:
        status = "fail"
    elif unverified_reasons:
        status = "unverified"
    else:
        status = "pass"

    return {
        "schema_version": "1",
        "run_id": manifest.get("run_id"),
        "status": status,
        "hard_checks": {"total": len(checks), "failed": len(failed_checks), "cases": checks},
        "metrics": metrics,
        "gates": gate_results,
        "blocking_reasons": blocking_reasons,
        "unverified_reasons": unverified_reasons,
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--rubric", type=Path)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--write-checks", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = evaluate_run(args.run_dir, args.contract, args.rubric)
        if args.write_checks:
            checks_dir = args.run_dir / "checks"
            checks_dir.mkdir(exist_ok=True)
            for check in result["hard_checks"]["cases"]:
                _write_json(checks_dir / f"{check['case_id']}.json", check)
        if args.write_report:
            _write_json(args.run_dir / "regression-summary.json", result)
    except (OSError, ValueError) as exc:
        print(f"V03_REGRESSION=ERROR {exc}")
        return 1
    print(
        "V03_REGRESSION="
        f"{result['status'].upper()} "
        f"hard_failed={result['hard_checks']['failed']} "
        f"skill_average={result['metrics']['skill_average_total']} "
        f"advantage={result['metrics']['skill_advantage']}"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

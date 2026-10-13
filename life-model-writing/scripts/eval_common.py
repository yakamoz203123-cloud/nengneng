"""Shared data contracts for the offline Skill evaluation tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ALLOWED_KINDS = {"content", "activation"}
ALLOWED_LENGTH_CONTRACTS = {"short", "standard", "long"}
EXPERIMENT_REQUIRED_FIELDS = {"engine", "condition", "repeat_index", "sampling"}


class EvaluationDataError(ValueError):
    """Raised when an evaluation file cannot satisfy the data contract."""

    def __init__(self, message: str, source: str, field_path: str) -> None:
        self.source = source
        self.field_path = field_path
        super().__init__(f"{source}:{field_path}: {message}")


def _error(message: str, source: str, field_path: str) -> EvaluationDataError:
    return EvaluationDataError(message, source, field_path)


def read_json(path: Path) -> dict[str, object]:
    """Read a UTF-8 JSON object and convert parse errors to a stable error."""

    source = str(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise _error(str(exc), source, "$") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _error(exc.msg, source, f"line {exc.lineno}, column {exc.colno}") from exc

    if not isinstance(data, dict):
        raise _error("top level must be an object", source, "$")
    return data


def normalize_case_id(value: str | int) -> str:
    """Normalize supported case identifiers without accepting booleans."""

    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("case id must be a string or integer")
    normalized = str(value).strip()
    if not normalized:
        raise ValueError("case id must not be empty")
    return normalized


def _required_string(
    item: dict[str, Any], key: str, source: str, field_path: str
) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _error("must be a non-empty string", source, f"{field_path}.{key}")
    return value


def validate_experiment_metadata(
    value: object, source: str = "experiment"
) -> dict[str, object]:
    """Validate metadata needed to reproduce a model comparison run."""

    if not isinstance(value, dict):
        raise _error("must be an object", source, "$")
    missing = EXPERIMENT_REQUIRED_FIELDS - set(value)
    if missing:
        field = sorted(missing)[0]
        raise _error("required field is missing", source, f"$.{field}")

    engine = value.get("engine")
    if not isinstance(engine, str) or not engine.strip():
        raise _error("must be a non-empty string", source, "$.engine")
    condition = value.get("condition")
    if not isinstance(condition, str) or not condition.strip():
        raise _error("must be a non-empty string", source, "$.condition")

    repeat_index = value.get("repeat_index")
    if (
        isinstance(repeat_index, bool)
        or not isinstance(repeat_index, int)
        or repeat_index < 0
    ):
        raise _error("must be a non-negative integer", source, "$.repeat_index")

    sampling = value.get("sampling")
    if not isinstance(sampling, dict):
        raise _error("must be an object", source, "$.sampling")
    temperature = sampling.get("temperature")
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or temperature < 0
    ):
        raise _error(
            "temperature must be a non-negative number",
            source,
            "$.sampling.temperature",
        )
    if "seed" in sampling:
        seed = sampling["seed"]
        if seed is not None and (
            isinstance(seed, bool) or not isinstance(seed, int)
        ):
            raise _error(
                "seed must be an integer or null",
                source,
                "$.sampling.seed",
            )

    return {
        "engine": engine,
        "condition": condition,
        "repeat_index": repeat_index,
        "sampling": dict(sampling),
    }


def validate_case_set(
    data: dict[str, object], source: str
) -> list[dict[str, object]]:
    """Validate and normalize one case-set document."""

    if not isinstance(data, dict):
        raise _error("top level must be an object", source, "$")
    _required_string(data, "skill_name", source, "$")
    _required_string(data, "version", source, "$")

    raw_cases = data.get("evals")
    if not isinstance(raw_cases, list):
        raise _error("must be a list", source, "evals")

    normalized: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for index, raw_case in enumerate(raw_cases):
        field_path = f"evals[{index}]"
        if not isinstance(raw_case, dict):
            raise _error("must be an object", source, field_path)

        raw_id = raw_case.get("id")
        try:
            case_id = normalize_case_id(raw_id)  # type: ignore[arg-type]
        except ValueError as exc:
            raise _error(str(exc), source, f"{field_path}.id") from exc
        if case_id in seen_ids:
            raise _error("duplicate case id", source, f"{field_path}.id")
        seen_ids.add(case_id)

        name = _required_string(raw_case, "name", source, field_path)
        prompt = _required_string(raw_case, "prompt", source, field_path)
        expected_output = _required_string(
            raw_case, "expected_output", source, field_path
        )

        assertions = raw_case.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            raise _error(
                "must be a non-empty list", source, f"{field_path}.assertions"
            )
        if any(not isinstance(assertion, str) or not assertion.strip() for assertion in assertions):
            raise _error(
                "must contain only non-empty strings",
                source,
                f"{field_path}.assertions",
            )

        kind = raw_case.get("kind", "content")
        if kind not in ALLOWED_KINDS:
            raise _error(
                f"must be one of {sorted(ALLOWED_KINDS)}",
                source,
                f"{field_path}.kind",
            )

        length_contract = raw_case.get("length_contract")
        if length_contract is not None and length_contract not in ALLOWED_LENGTH_CONTRACTS:
            raise _error(
                f"must be one of {sorted(ALLOWED_LENGTH_CONTRACTS)} or null",
                source,
                f"{field_path}.length_contract",
            )

        expected_activation = raw_case.get("expected_activation")
        if expected_activation is not None and not isinstance(expected_activation, bool):
            raise _error(
                "must be a boolean or null",
                source,
                f"{field_path}.expected_activation",
            )

        normalized.append(
            {
                "id": case_id,
                "name": name,
                "kind": kind,
                "prompt": prompt,
                "expected_output": expected_output,
                "assertions": list(assertions),
                "length_contract": length_contract,
                "expected_activation": expected_activation,
                "source": source,
            }
        )

    return normalized


def load_case_sets(paths: list[Path]) -> list[dict[str, object]]:
    """Load multiple case sets and reject duplicate IDs across files."""

    all_cases: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for path in paths:
        cases = validate_case_set(read_json(path), str(path))
        for index, case in enumerate(cases):
            case_id = str(case["id"])
            if case_id in seen_ids:
                raise _error("duplicate case id across case sets", str(path), f"evals[{index}].id")
            seen_ids.add(case_id)
            all_cases.append(case)
    return all_cases

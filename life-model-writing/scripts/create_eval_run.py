"""Create an immutable-layout evaluation run before outputs are imported."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval_common import load_case_sets, validate_experiment_metadata


RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _git_head(start: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "HEAD"],
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return "unknown"
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def _timestamp(value: datetime | None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat()


def _validate_run_inputs(
    skill_root: Path,
    run_id: str,
    model: dict[str, object],
    invocation_mode: str,
    human_intervention: str,
) -> None:
    if not run_id or not RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must contain only letters, digits, '.', '_' or '-'")
    if not isinstance(model, dict) or not isinstance(model.get("name"), str) or not model["name"].strip():
        raise ValueError("model.name must be a non-empty string")
    if not invocation_mode.strip():
        raise ValueError("invocation_mode must not be empty")
    if not human_intervention.strip():
        raise ValueError("human_intervention must not be empty")
    if not skill_root.parent.exists():
        raise ValueError("skill_root parent must exist")


def create_run(
    skill_root: Path,
    case_paths: list[Path],
    run_id: str,
    model: dict[str, object],
    invocation_mode: str,
    human_intervention: str,
    experiment: dict[str, object] | None = None,
    now: datetime | None = None,
) -> Path:
    """Validate inputs, then create one collision-safe evaluation run."""

    skill_root = Path(skill_root)
    _validate_run_inputs(skill_root, run_id, model, invocation_mode, human_intervention)
    normalized_experiment = (
        validate_experiment_metadata(experiment, "experiment")
        if experiment is not None
        else None
    )
    cases = load_case_sets([Path(path) for path in case_paths])

    run_path = skill_root / "evals" / "runs" / run_id
    if run_path.exists():
        raise FileExistsError(f"evaluation run already exists: {run_path}")

    manifest_cases: list[dict[str, object]] = []
    for case in cases:
        prompt = str(case["prompt"])
        manifest_cases.append(
            {
                "id": case["id"],
                "name": case["name"],
                "kind": case["kind"],
                "source": case["source"],
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "length_contract": case["length_contract"],
                "expected_activation": case["expected_activation"],
            }
        )

    manifest: dict[str, Any] = {
        "schema_version": "1",
        "run_id": run_id,
        "created_at": _timestamp(now),
        "skill_name": "life-model-writing",
        "git_commit": _git_head(skill_root.parent),
        "model": model,
        "invocation_mode": invocation_mode,
        "human_intervention": human_intervention,
        "case_sets": [str(Path(path)) for path in case_paths],
        "cases": manifest_cases,
    }
    if normalized_experiment is not None:
        manifest["experiment"] = normalized_experiment

    run_path.mkdir(parents=True)
    for directory in ("outputs", "checks", "scores"):
        (run_path / directory).mkdir()
    _write_json(run_path / "manifest.json", manifest)
    return run_path


def _parse_parameters(value: str) -> dict[str, object]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("--parameters-json must contain a JSON object")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", type=Path, required=True)
    parser.add_argument("--cases", type=Path, nargs="+", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--backend-version", default="unknown")
    parser.add_argument("--parameters-json", default="{}")
    parser.add_argument("--invocation-mode", required=True)
    parser.add_argument("--human-intervention", required=True)
    args = parser.parse_args(argv)

    try:
        model = {
            "name": args.model_name,
            "backend_version": args.backend_version,
            "parameters": _parse_parameters(args.parameters_json),
        }
        run_path = create_run(
            skill_root=args.skill_root,
            case_paths=args.cases,
            run_id=args.run_id,
            model=model,
            invocation_mode=args.invocation_mode,
            human_intervention=args.human_intervention,
        )
    except (ValueError, OSError) as exc:
        print(f"EVALUATION_RUN=ERROR {exc}")
        return 1

    print(f"EVALUATION_RUN=CREATED {run_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

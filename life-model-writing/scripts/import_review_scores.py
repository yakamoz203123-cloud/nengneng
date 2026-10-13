"""Import independently produced score JSON files back into an evaluation run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from eval_common import read_json
from score_eval_run import validate_score


SAFE_CASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _read_json_value(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {path}") from exc


def _packet_case_ids(packet_dir: Path) -> set[str]:
    cases = _read_json_value(packet_dir / "cases.json")
    if not isinstance(cases, list):
        raise ValueError("packet cases must be a list")
    case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            raise ValueError("packet cases must contain string ids")
        case_ids.add(case["id"])
    return case_ids


def _packet_case_mapping(packet_dir: Path, case_ids: set[str]) -> dict[str, str]:
    """Load the private blind-to-source map, with legacy identity fallback."""

    mapping_path = packet_dir.with_name(f"{packet_dir.name}.mapping.json")
    if not mapping_path.is_file():
        return {case_id: case_id for case_id in case_ids}

    data = _read_json_value(mapping_path)
    if not isinstance(data, dict) or not isinstance(data.get("blind_to_source"), dict):
        raise ValueError("invalid blind review mapping")
    raw_mapping = data["blind_to_source"]
    mapping: dict[str, str] = {}
    for blind_id, source_id in raw_mapping.items():
        if (
            not isinstance(blind_id, str)
            or not isinstance(source_id, str)
            or not SAFE_CASE_ID.fullmatch(blind_id)
            or not SAFE_CASE_ID.fullmatch(source_id)
        ):
            raise ValueError("invalid blind review mapping ids")
        mapping[blind_id] = source_id
    if set(mapping) != case_ids:
        raise ValueError("blind review mapping does not cover packet cases")
    return mapping


def import_review_scores(
    run_dir: Path,
    packet_dir: Path,
    rubric_path: Path,
) -> list[dict[str, object]]:
    """Validate and exclusively import independent packet scores."""

    run_dir = Path(run_dir)
    packet_dir = Path(packet_dir)
    rubric = read_json(Path(rubric_path))
    if not isinstance(rubric, dict):
        raise ValueError("rubric must be an object")
    packet_case_ids = _packet_case_ids(packet_dir)
    packet_mapping = _packet_case_mapping(packet_dir, packet_case_ids)
    source_dir = packet_dir / "scores"
    if not source_dir.is_dir():
        raise FileNotFoundError(source_dir)
    destination_dir = run_dir / "scores"
    destination_dir.mkdir(exist_ok=True)

    imported: list[dict[str, object]] = []
    for source in sorted(source_dir.glob("*.json")):
        blind_case_id = source.stem
        if not SAFE_CASE_ID.fullmatch(blind_case_id):
            raise ValueError(f"unsafe score filename: {source.name}")
        if blind_case_id not in packet_case_ids:
            raise ValueError(f"score case is not in review packet: {blind_case_id}")

        score = read_json(source)
        if not isinstance(score, dict):
            raise ValueError(f"score must be an object: {source.name}")
        evaluator = score.get("evaluator")
        if not isinstance(evaluator, dict) or evaluator.get("independent") is not True:
            raise ValueError(f"score is not marked independent: {source.name}")
        normalized = validate_score(score, rubric, blind_case_id)

        source_case_id = packet_mapping[blind_case_id]
        destination = destination_dir / f"{source_case_id}.json"
        if destination.exists():
            raise FileExistsError(f"score already exists: {destination}")
        raw_bytes = source.read_bytes()
        with destination.open("xb") as output_file:
            output_file.write(raw_bytes)
        if destination.read_bytes() != raw_bytes:
            destination.unlink()
            raise OSError(f"score byte verification failed: {destination}")
        imported.append(
            {
                "case_id": source_case_id,
                "status": normalized["status"],
                "byte_length": len(raw_bytes),
                "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            }
        )
    return imported


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--rubric", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        imported = import_review_scores(
            run_dir=args.run_dir,
            packet_dir=args.packet_dir,
            rubric_path=args.rubric,
        )
    except (OSError, ValueError) as exc:
        print(f"REVIEW_SCORES=ERROR {exc}")
        return 1

    print(f"REVIEW_SCORES=IMPORTED {len(imported)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

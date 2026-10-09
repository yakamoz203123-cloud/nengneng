"""Import generated evaluation outputs without changing their bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from eval_common import normalize_case_id


SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _read_manifest(run_path: Path) -> tuple[Path, dict[str, object]]:
    manifest_path = run_path / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"manifest is missing: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid manifest: {manifest_path}") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("cases"), list):
        raise ValueError("manifest cases must be a list")
    return manifest_path, manifest


def _case_ids(manifest: dict[str, object]) -> set[str]:
    ids: set[str] = set()
    for case in manifest["cases"]:
        if isinstance(case, dict) and "id" in case:
            ids.add(normalize_case_id(case["id"]))  # type: ignore[arg-type]
    return ids


def _write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def import_output(run_dir: Path, case_id: str, source: Path) -> dict[str, object]:
    """Import one output and append its digest record to the manifest."""

    run_dir = Path(run_dir)
    source = Path(source)
    manifest_path, manifest = _read_manifest(run_dir)
    normalized_id = normalize_case_id(case_id)
    if not SAFE_FILENAME.fullmatch(normalized_id):
        raise ValueError("case id is not safe for an output filename")
    if normalized_id not in _case_ids(manifest):
        raise ValueError(f"unknown case id: {normalized_id}")
    if not source.is_file():
        raise FileNotFoundError(source)

    output_dir = run_dir / "outputs"
    output_dir.mkdir(exist_ok=True)
    destination = output_dir / f"{normalized_id}.md"
    if destination.exists():
        raise FileExistsError(f"output already exists: {destination}")

    source_bytes = source.read_bytes()
    with destination.open("xb") as output_file:
        output_file.write(source_bytes)
    if destination.read_bytes() != source_bytes:
        destination.unlink()
        raise OSError(f"byte verification failed: {destination}")

    record: dict[str, object] = {
        "case_id": normalized_id,
        "source_filename": source.name,
        "byte_length": len(source_bytes),
        "sha256": hashlib.sha256(source_bytes).hexdigest(),
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }
    outputs = manifest.setdefault("outputs", [])
    if not isinstance(outputs, list):
        raise ValueError("manifest outputs must be a list")
    if any(isinstance(item, dict) and item.get("case_id") == normalized_id for item in outputs):
        raise FileExistsError(f"output record already exists: {normalized_id}")
    outputs.append(record)
    outputs.sort(key=lambda item: str(item.get("case_id", "")) if isinstance(item, dict) else "")
    _write_manifest(manifest_path, manifest)
    return record


def import_output_directory(run_dir: Path, source_dir: Path) -> list[dict[str, object]]:
    """Import every Markdown output present; missing expected cases are allowed."""

    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise FileNotFoundError(source_dir)
    records: list[dict[str, object]] = []
    for source in sorted(source_dir.glob("*.md")):
        records.append(import_output(run_dir, source.stem, source))
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--source", type=Path)
    source_group.add_argument("--source-dir", type=Path)
    parser.add_argument("--case-id")
    args = parser.parse_args(argv)

    try:
        if args.source is not None:
            if not args.case_id:
                parser.error("--case-id is required with --source")
            records = [import_output(args.run_dir, args.case_id, args.source)]
        else:
            records = import_output_directory(args.run_dir, args.source_dir)
    except (OSError, ValueError) as exc:
        print(f"OUTPUT_IMPORT=ERROR {exc}")
        return 1

    print(f"OUTPUT_IMPORT=IMPORTED {len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Create a blinded independent-review packet from one evaluation run."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from eval_common import load_case_sets, read_json


REVIEWER_INSTRUCTIONS = """# Independent review

你是独立内容评审员。只使用本目录中的 `cases.json`、`rubric.json`、`skill/` 和 `outputs/`。

逐个阅读案例提示、Skill 入口、相关理论卡和对应原始输出。按照 rubric 的六个维度分别给出 0—5 分，说明证据、扣分原因和 critical_errors。不要参考其他运行、历史结论或预期分数，也不要因为语言流畅就默认理论正确。

请将每个案例的结果写成与 rubric 对应的 score JSON，并将 `evaluator.independent` 设置为 `true`。若某个案例没有原始输出，不要补写或猜测，直接记录为无法评分。
"""


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _resolve_case_sets(manifest: dict[str, object], skill_root: Path) -> list[Path]:
    values = manifest.get("case_sets")
    if not isinstance(values, list):
        raise ValueError("manifest.case_sets must be a list")

    paths: list[Path] = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError("manifest.case_sets must contain strings")
        raw = Path(value)
        candidates = [
            raw,
            skill_root.parent / raw,
            skill_root / raw,
        ]
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is None:
            raise FileNotFoundError(value)
        paths.append(path)
    return paths


def _case_map(manifest: dict[str, object], skill_root: Path) -> dict[str, dict[str, object]]:
    cases = load_case_sets(_resolve_case_sets(manifest, skill_root))
    return {str(case["id"]): case for case in cases}


def _copy_skill_context(skill_root: Path, destination: Path) -> None:
    skill_destination = destination / "skill"
    skill_destination.mkdir()
    shutil.copyfile(skill_root / "SKILL.md", skill_destination / "SKILL.md")
    shutil.copytree(skill_root / "references", skill_destination / "references")


def create_review_packet(
    run_dir: Path,
    skill_root: Path,
    rubric_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Create an exclusive packet containing only independent-review inputs."""

    run_dir = Path(run_dir)
    skill_root = Path(skill_root)
    rubric_path = Path(rubric_path)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"review packet already exists: {output_dir}")

    manifest = read_json(run_dir / "manifest.json")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("cases"), list):
        raise ValueError("manifest.cases must be a list")
    rubric = read_json(rubric_path)
    if not isinstance(rubric, dict):
        raise ValueError("rubric must be an object")
    cases_by_id = _case_map(manifest, skill_root)

    output_dir.mkdir(parents=True)
    (output_dir / "outputs").mkdir()
    _copy_skill_context(skill_root, output_dir)
    shutil.copyfile(rubric_path, output_dir / "rubric.json")
    (output_dir / "reviewer-instructions.md").write_text(
        REVIEWER_INSTRUCTIONS,
        encoding="utf-8",
    )

    review_cases: list[dict[str, object]] = []
    omitted_case_ids: list[str] = []
    output_records: list[dict[str, object]] = []
    blind_to_source: dict[str, str] = {}
    sample_index = 0
    for index, raw_case in enumerate(manifest["cases"], start=1):
        if not isinstance(raw_case, dict) or "id" not in raw_case:
            raise ValueError("manifest contains an invalid case")
        case_id = str(raw_case["id"])
        source_output = run_dir / "outputs" / f"{case_id}.md"
        if not source_output.is_file():
            omitted_case_ids.append(f"omitted-{index:03d}")
            continue
        source_case = cases_by_id.get(case_id)
        if source_case is None:
            raise ValueError(f"case is missing from case sets: {case_id}")

        sample_index += 1
        blind_id = f"sample-{sample_index:03d}"
        blind_to_source[blind_id] = case_id
        destination_output = output_dir / "outputs" / f"{blind_id}.md"
        output_bytes = source_output.read_bytes()
        destination_output.write_bytes(output_bytes)
        review_cases.append(
            {
                "id": blind_id,
                "name": blind_id,
                "kind": str(source_case["kind"]),
                "prompt": str(source_case["prompt"]),
                "length_contract": source_case.get("length_contract"),
            }
        )
        output_records.append(
            {
                "case_id": blind_id,
                "filename": destination_output.name,
                "byte_length": len(output_bytes),
                "sha256": hashlib.sha256(output_bytes).hexdigest(),
            }
        )

    _write_json(output_dir / "cases.json", review_cases)
    packet_manifest: dict[str, object] = {
        "schema_version": "1",
        "source_run_id": manifest.get("run_id"),
        "case_count": len(review_cases),
        "omitted_case_ids": omitted_case_ids,
        "outputs": output_records,
    }
    _write_json(output_dir / "manifest.json", packet_manifest)
    _write_json(
        output_dir.with_name(f"{output_dir.name}.mapping.json"),
        {
            "schema_version": "1",
            "source_run_id": manifest.get("run_id"),
            "blind_to_source": blind_to_source,
        },
    )
    return packet_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--skill-root", type=Path, required=True)
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        manifest = create_review_packet(
            run_dir=args.run_dir,
            skill_root=args.skill_root,
            rubric_path=args.rubric,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError) as exc:
        print(f"REVIEW_PACKET=ERROR {exc}")
        return 1

    print(
        "REVIEW_PACKET=CREATED "
        f"cases={manifest['case_count']} "
        f"omitted={len(manifest['omitted_case_ids'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

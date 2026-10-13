"""Generate one reproducible DeepSeek paired evaluation run."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from create_eval_run import create_run
from deepseek_provider import DEFAULT_MODEL, DeepSeekAPIError, call_chat_completion
from eval_common import load_case_sets
from import_outputs import import_output
from reference_router import build_skill_context, load_routes
from score_eval_run import LENGTH_BOUNDS, check_output, count_non_whitespace_characters


ORDINARY_SYSTEM = """你是一名中文长口播文案作者。
请围绕用户给出的生活问题，写一版800—1200字、可以直接朗读的中文口播文案。
要求：从具体生活场景开头；解释现象形成的原因；语言自然，不写成论文；不编造研究、数据、机构或来源；如果结论有条件，请说明边界和例外；只输出最终口播文案，不展示分析过程。
先在内部完成草稿，再检查非空白字符数。标准版以950—1100个非空白字符为安全目标；超过 1100 字必须再压缩一轮，先删重复场景、同义案例、重复变量和结论，再缩短不改变预测的理论定义；不要用截断代替压缩。低于800字时只补缺失的机制桥梁或边界，不用空话凑字数。"""

SKILL_SYSTEM_PREFIX = """你正在执行下面提供的 life-model-writing Skill。
最终只输出一版800—1200字、可以直接朗读的中文口播文案，不输出内部分析、模型卡、评分或提纲。
先在内部完成草稿，再检查非空白字符数。标准版以950—1100个非空白字符为安全目标；超过 1100 字必须再压缩一轮，先删重复场景、同义案例、重复变量和结论，再缩短不改变预测的理论定义；不要用截断代替压缩。低于800字时只补缺失的机制桥梁或边界，不用空话凑字数。

"""

OVERLENGTH_REPAIR_INSTRUCTION = """上一版口播文案超过了标准版的 1200 个非空白字符上限。
请在保留核心因果链、关键变量关系、一个反事实或适用边界，以及必要定量关系的前提下，压缩上一版。
只输出压缩后的完整口播文案，不输出解释、修改说明、提纲或评分；不要截断，不要只删除结尾，不要重新扩写。
压缩优先删除重复场景、同义案例、重复结论和非关键修饰，再合并理论定义；目标是 950—1100 个非空白字符，最终必须控制在 800—1200 个非空白字符内。"""

UNDERLENGTH_REPAIR_INSTRUCTION = """上一版口播文案低于标准版的 800 个非空白字符下限。
请在保留原有主线的基础上，补充缺失的机制桥梁、关键变量关系、一个反事实或适用边界，以及必要的定量关系。
只输出补充后的完整口播文案，不输出解释、修改说明、提纲或评分；不要用空洞金句、重复场景或无关案例凑字数。
目标是 950—1100 个非空白字符，最终必须控制在 800—1200 个非空白字符内。"""

MAX_LENGTH_REPAIR_PASSES = 2


def normalize_case_records(data: dict[str, object]) -> dict[str, dict[str, str]]:
    raw_cases = data.get("evals")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("v0.5 cases.evals must be a non-empty list")
    records: dict[str, dict[str, str]] = {}
    pairs: dict[str, set[str]] = {}
    prompts: dict[str, str] = {}
    for index, raw in enumerate(raw_cases):
        if not isinstance(raw, dict):
            raise ValueError(f"case {index} must be an object")
        case_id = raw.get("id")
        pair_id = raw.get("pair_id")
        condition = raw.get("condition")
        prompt = raw.get("prompt")
        if not all(isinstance(value, str) and value.strip() for value in (case_id, pair_id, condition, prompt)):
            raise ValueError(f"case {index} has invalid id, pair_id, condition, or prompt")
        if condition not in {"ordinary", "skill"}:
            raise ValueError(f"case {case_id} condition must be ordinary or skill")
        if case_id in records:
            raise ValueError(f"duplicate case id: {case_id}")
        if pair_id in prompts and prompts[pair_id] != prompt:
            raise ValueError(f"paired cases must use identical prompts: {pair_id}")
        prompts[pair_id] = prompt
        pairs.setdefault(pair_id, set()).add(condition)
        records[case_id] = {
            "id": case_id,
            "pair_id": pair_id,
            "condition": condition,
            "prompt": prompt,
        }
    for pair_id, conditions in pairs.items():
        if conditions != {"ordinary", "skill"}:
            raise ValueError(f"pair must contain ordinary and skill cases: {pair_id}")
    return records


def build_messages(
    condition: str, topic: str, skill_context: str
) -> list[dict[str, str]]:
    if condition == "ordinary":
        system = ORDINARY_SYSTEM
    elif condition == "skill":
        system = SKILL_SYSTEM_PREFIX + skill_context
    else:
        raise ValueError("condition must be ordinary or skill")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": topic},
    ]


def standard_length_violation(
    case: dict[str, object], content: str
) -> str | None:
    """Return one standard-length violation, if a bounded repair is warranted."""

    contract = case.get("length_contract")
    if contract != "standard":
        return None
    lower, upper = LENGTH_BOUNDS["standard"]
    character_count = count_non_whitespace_characters(content)
    if character_count < lower:
        return "underlength"
    if character_count > upper:
        return "overlength"
    return None


def build_length_repair_messages(
    original_messages: list[dict[str, str]], draft: str, violation: str
) -> list[dict[str, str]]:
    """Ask the same condition/model to repair one standard-length violation."""

    if violation == "overlength":
        instruction = OVERLENGTH_REPAIR_INSTRUCTION
    elif violation == "underlength":
        instruction = UNDERLENGTH_REPAIR_INSTRUCTION
    else:
        raise ValueError("violation must be underlength or overlength")

    return [
        *original_messages,
        {"role": "assistant", "content": draft},
        {"role": "user", "content": instruction},
    ]


def build_output_check(case: dict[str, object], output_path: Path) -> dict[str, object]:
    """Reuse the existing deterministic output contract for provider runs."""

    return check_output(case, output_path)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_raw_cases(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("cases must be a JSON object")
    return data


def _subset_case_data(
    data: dict[str, object], selected_ids: set[str]
) -> dict[str, object]:
    raw_cases = data.get("evals")
    if not isinstance(raw_cases, list):
        raise ValueError("v0.5 cases.evals must be a list")
    return {
        **data,
        "evals": [
            raw_case
            for raw_case in raw_cases
            if isinstance(raw_case, dict) and raw_case.get("id") in selected_ids
        ],
    }


def _set_manifest_case_source(manifest: dict[str, object], source_path: Path) -> None:
    raw_cases = manifest.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("manifest.cases must be a list")
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise ValueError("manifest.cases must contain objects")
        raw_case["source"] = str(source_path)


def _write_reveal(run_dir: Path, records: dict[str, dict[str, str]]) -> None:
    pairs: dict[str, dict[str, str]] = {}
    for record in records.values():
        pair = pairs.setdefault(record["pair_id"], {"pair_id": record["pair_id"]})
        pair[f"{record['condition']}_case_id"] = record["id"]
    _write_json(run_dir / "reveal.json", {"pairs": [pairs[key] for key in sorted(pairs)]})


def run_eval(
    *,
    skill_root: Path,
    cases_path: Path,
    routes_path: Path,
    run_id: str,
    repeat_index: int,
    api_key: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    thinking: str = "disabled",
    max_tokens: int = 3000,
    timeout: int = 180,
    pair_ids: set[str] | None = None,
) -> Path:
    raw_data = _load_raw_cases(cases_path)
    records = normalize_case_records(raw_data)
    if pair_ids is not None:
        records = {
            case_id: record
            for case_id, record in records.items()
            if record["pair_id"] in pair_ids
        }
        selected_pairs = {record["pair_id"] for record in records.values()}
        if selected_pairs != pair_ids:
            missing = sorted(pair_ids - selected_pairs)
            raise ValueError(f"unknown or incomplete pair ids: {missing}")

    with tempfile.TemporaryDirectory(prefix="life-model-deepseek-output-") as temporary:
        temporary_root = Path(temporary)
        selected_case_path = cases_path
        if pair_ids is not None:
            selected_case_path = temporary_root / "selected-cases.json"
            selected_case_path.write_text(
                json.dumps(
                    _subset_case_data(raw_data, set(records)),
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        # create_run validates the regular case-set shape and records prompt hashes.
        run_dir = create_run(
            skill_root=skill_root,
            case_paths=[selected_case_path],
            run_id=run_id,
            model={
                "name": model,
                "backend_version": "deepseek-api",
                "parameters": {
                    "temperature": temperature,
                    "thinking": thinking,
                    "max_tokens": max_tokens,
                },
            },
            invocation_mode="deepseek-api",
            human_intervention="none",
            experiment={
                "engine": "deepseek",
                "condition": "paired-ab",
                "repeat_index": repeat_index,
                "sampling": {"temperature": temperature, "seed": None},
            },
        )
        if pair_ids is not None:
            manifest_path = run_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["case_sets"] = [str(cases_path)]
            _set_manifest_case_source(manifest, cases_path)
            _write_json(manifest_path, manifest)
        _write_reveal(run_dir, records)
        routes = load_routes(routes_path, skill_root)
        normalized_cases = {
            str(case["id"]): case for case in load_case_sets([selected_case_path])
        }
        temporary_root = temporary_root / "outputs"
        temporary_root.mkdir()
        for case_id in sorted(records):
            record = records[case_id]
            if record["condition"] == "skill":
                context, reference_files = build_skill_context(
                    skill_root, routes, record["pair_id"]
                )
            else:
                context, reference_files = "", []
            messages = build_messages(record["condition"], record["prompt"], context)
            initial_result = call_chat_completion(
                api_key,
                messages,
                model=model,
                temperature=temperature,
                thinking=thinking,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            initial_content = str(initial_result["content"])
            attempt_dir = run_dir / "attempts" / case_id
            attempt_dir.mkdir(parents=True, exist_ok=True)
            (attempt_dir / "initial.md").write_text(initial_content, encoding="utf-8")

            result = initial_result
            final_content = initial_content
            length_violation = standard_length_violation(
                normalized_cases[case_id], initial_content
            )
            initial_length_violation = length_violation
            repair_attempted = length_violation is not None
            repair_passes = 0
            repair_status = "not-needed"
            repair_error: str | None = None
            while (
                length_violation is not None
                and repair_passes < MAX_LENGTH_REPAIR_PASSES
            ):
                repair_passes += 1
                try:
                    result = call_chat_completion(
                        api_key,
                        build_length_repair_messages(
                            messages, final_content, str(length_violation)
                        ),
                        model=model,
                        temperature=temperature,
                        thinking=thinking,
                        max_tokens=max_tokens,
                        timeout=timeout,
                    )
                    final_content = str(result["content"])
                    (attempt_dir / f"repair-{repair_passes}.md").write_text(
                        final_content, encoding="utf-8"
                    )
                    length_violation = standard_length_violation(
                        normalized_cases[case_id], final_content
                    )
                except DeepSeekAPIError as exc:
                    repair_status = "failed"
                    repair_error = str(exc)
                    break

            if repair_attempted and repair_error is None:
                repair_status = "applied" if length_violation is None else "exhausted"

            source = temporary_root / f"{case_id}.md"
            source.write_text(final_content, encoding="utf-8")
            import_output(run_dir, case_id, source)
            output_path = run_dir / "outputs" / f"{case_id}.md"
            _write_json(
                run_dir / "checks" / f"{case_id}.json",
                build_output_check(normalized_cases[case_id], output_path),
            )
            record_dir = run_dir / "provider-records"
            record_dir.mkdir(exist_ok=True)
            _write_json(
                record_dir / f"{case_id}.json",
                {
                    "case_id": case_id,
                    "pair_id": record["pair_id"],
                    "condition": record["condition"],
                    "model": result["model"],
                    "finish_reason": result["finish_reason"],
                    "usage": result["usage"],
                    "reference_files": reference_files,
                    "initial": {
                        "model": initial_result["model"],
                        "finish_reason": initial_result["finish_reason"],
                        "usage": initial_result["usage"],
                        "character_count": count_non_whitespace_characters(
                            initial_content
                        ),
                    },
                    "compression_repair": {
                        "attempted": repair_attempted,
                        "initial_violation": initial_length_violation,
                        "final_violation": length_violation,
                        "passes": repair_passes,
                        "status": repair_status,
                        "error": repair_error,
                        "final_character_count": count_non_whitespace_characters(
                            final_content
                        ),
                    },
                },
            )
    return run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--routes", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repeat-index", type=int, required=True)
    parser.add_argument("--pair-id", action="append", dest="pair_ids")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--thinking", choices=("enabled", "disabled"), default="disabled")
    parser.add_argument("--max-tokens", type=int, default=3000)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    raw_data = _load_raw_cases(args.cases)
    records = normalize_case_records(raw_data)
    selected_pairs = set(args.pair_ids) if args.pair_ids else set(record["pair_id"] for record in records.values())
    if args.dry_run:
        print(f"DEEPSEEK_DRY_RUN pairs={len(selected_pairs)} cases={len([r for r in records.values() if r['pair_id'] in selected_pairs])}")
        return 0
    if not args.allow_paid:
        print("DEEPSEEK_RUN=BLOCKED missing --allow-paid")
        return 2
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key.strip():
        print("DEEPSEEK_RUN=BLOCKED missing DEEPSEEK_API_KEY")
        return 2
    run_dir = run_eval(
        skill_root=args.skill_root,
        cases_path=args.cases,
        routes_path=args.routes,
        run_id=args.run_id,
        repeat_index=args.repeat_index,
        api_key=api_key,
        model=args.model,
        temperature=args.temperature,
        thinking=args.thinking,
        max_tokens=args.max_tokens,
        timeout=args.timeout,
        pair_ids=selected_pairs,
    )
    print(f"DEEPSEEK_RUN=CREATED {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

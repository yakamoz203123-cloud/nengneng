"""Resumable, page-scoped production queue for picturebook image generation.

This module deliberately does not call an image API.  The host image tool owns
generation; this queue owns the book plan, one job per page, bounded claims,
atomic state, cache checks, retries, and page-local revisions.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_MAX_IN_FLIGHT = 2
DEFAULT_MAX_ATTEMPTS = 2
ACTIVE_STATUSES = {"running"}
DONE_STATUSES = {"completed", "cached"}
RETRYABLE_STATUSES = {"pending", "retryable"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"required JSON file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_book_path(book_dir: Path, relative_or_absolute: str | None) -> Path | None:
    if not relative_or_absolute:
        return None
    candidate = Path(relative_or_absolute)
    if not candidate.is_absolute():
        candidate = book_dir / candidate
    return candidate.resolve()


def _relative_to_book(book_dir: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(book_dir.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"path must stay inside book directory: {path}") from exc


def _page_number(page: dict[str, Any], index: int) -> int:
    raw = page.get("page", index)
    try:
        number = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid page number at index {index}: {raw!r}") from exc
    if number < 1:
        raise ValueError(f"page number must be positive: {number}")
    return number


def _pages(document: dict[str, Any], name: str) -> list[dict[str, Any]]:
    pages = document.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError(f"{name} must contain a non-empty pages list")
    if not all(isinstance(page, dict) for page in pages):
        raise ValueError(f"{name}.pages must contain objects")
    return pages


def _plan(book_dir: Path) -> dict[str, Any]:
    book_dir = book_dir.resolve()
    story_path = book_dir / "story.md"
    if not story_path.exists() or not story_path.read_text(encoding="utf-8").strip():
        raise ValueError("complete story is required before image generation: story.md")

    manifest = _read_json(book_dir / "page-manifest.json")
    storyboard = _read_json(book_dir / "storyboard.json")
    layout = _read_json(book_dir / "layout.json")
    manifest_pages = _pages(manifest, "page-manifest.json")
    storyboard_pages = _pages(storyboard, "storyboard.json")
    layout_pages = _pages(layout, "layout.json")
    if not (len(manifest_pages) == len(storyboard_pages) == len(layout_pages)):
        raise ValueError("storyboard, page manifest, and layout must be complete for the same page count")

    manifest_by_page: dict[int, dict[str, Any]] = {}
    storyboard_by_page: dict[int, dict[str, Any]] = {}
    layout_by_page: dict[int, dict[str, Any]] = {}
    for index, page in enumerate(manifest_pages, start=1):
        number = _page_number(page, index)
        if number in manifest_by_page:
            raise ValueError(f"duplicate page in page-manifest.json: {number}")
        manifest_by_page[number] = page
    for index, page in enumerate(storyboard_pages, start=1):
        number = _page_number(page, index)
        storyboard_by_page[number] = page
    for index, page in enumerate(layout_pages, start=1):
        number = _page_number(page, index)
        layout_by_page[number] = page
    page_numbers = sorted(manifest_by_page)
    if page_numbers != sorted(storyboard_by_page) or page_numbers != sorted(layout_by_page):
        raise ValueError("storyboard, page manifest, and layout page numbers must match")

    ages = {str(manifest.get("age_band", "")).strip()}
    character_versions: set[str] = set()
    character_paths: set[str] = set()
    style_versions: set[str] = set()
    jobs: list[dict[str, Any]] = []
    for number in page_numbers:
        page = manifest_by_page[number]
        prompt_path_value = page.get("current_prompt_path") or page.get("prompt_path")
        if not isinstance(prompt_path_value, str) or not prompt_path_value.strip():
            raise ValueError(f"page {number} is missing its completed prompt path")
        prompt_path = _resolve_book_path(book_dir, prompt_path_value)
        if prompt_path is None or not prompt_path.is_file():
            raise ValueError(f"page {number} prompt does not exist: {prompt_path_value}")

        character_path_value = page.get("character_reference_path")
        if not isinstance(character_path_value, str) or not character_path_value.strip():
            raise ValueError(f"page {number} is missing character_reference_path")
        character_path = _resolve_book_path(book_dir, character_path_value)
        if character_path is None or not character_path.is_file():
            raise ValueError(f"page {number} character reference does not exist: {character_path_value}")

        production_path_value = page.get("production_reference_path") or character_path_value
        production_path = _resolve_book_path(book_dir, production_path_value)
        if production_path is None or not production_path.is_file():
            raise ValueError(f"page {number} production reference does not exist: {production_path_value}")

        character_versions.add(str(page.get("characters_version", "")).strip())
        character_paths.add(Path(character_path_value).as_posix())
        layout_page = layout_by_page[number]
        style_value = layout_page.get("style_version") or layout_page.get("layout_style_version")
        if style_value is not None:
            style_versions.add(str(style_value).strip())
        prompt_hash = _file_hash(prompt_path)
        ref_hash = _file_hash(character_path)
        production_hash = _file_hash(production_path)
        layout_fingerprint = {
            "layout": layout_page,
            "layout_file": _canonical_hash(layout),
        }
        base_fingerprint = _canonical_hash(
            {
                "book_title": manifest.get("title"),
                "age_band": manifest.get("age_band"),
                "page": number,
                "manifest_page": page,
                "storyboard_page": storyboard_by_page[number],
                "prompt_hash": prompt_hash,
                "character_reference": Path(character_path_value).as_posix(),
                "character_hash": ref_hash,
                "production_reference": Path(production_path_value).as_posix(),
                "production_hash": production_hash,
                "layout_fingerprint": layout_fingerprint,
            }
        )
        current_output = page.get("current_image_path")
        output_path = _resolve_book_path(book_dir, current_output)
        if output_path is None:
            output_path = book_dir / "images" / f"page-{number:02d}.png"
        output_relative = _relative_to_book(book_dir, output_path)
        cached = output_path.is_file()
        jobs.append(
            {
                "job_id": f"page-{number:02d}",
                "page": number,
                "revision": 1,
                "status": "cached" if cached else "pending",
                "attempts": 0,
                "max_attempts": DEFAULT_MAX_ATTEMPTS,
                "request_fingerprint": base_fingerprint,
                "base_request_fingerprint": base_fingerprint,
                "prompt_path": Path(prompt_path_value).as_posix(),
                "character_reference_path": Path(character_path_value).as_posix(),
                "production_reference_path": Path(production_path_value).as_posix(),
                "output_path": output_relative,
                "previous_output_path": None,
                "output_sha256": _file_hash(output_path) if cached else None,
                "errors": [],
                "elapsed_ms": None,
                "created_at": _now(),
                "updated_at": _now(),
            }
        )

    if len(ages) != 1 or "" in ages:
        raise ValueError("all pages must use one confirmed age band")
    if len(character_versions) != 1 or "" in character_versions:
        raise ValueError("all pages must use one approved character-bible version")
    if len(character_paths) != 1:
        raise ValueError("all pages must use the same character reference path")
    if len(style_versions) > 1:
        raise ValueError("all pages must use one approved layout/style version")

    plan_fingerprint = _canonical_hash(
        {
            "story_sha256": _file_hash(story_path),
            "manifest": manifest,
            "storyboard": storyboard,
            "layout": layout,
            "jobs": [{"page": job["page"], "fingerprint": job["base_request_fingerprint"]} for job in jobs],
        }
    )
    return {
        "book_dir": str(book_dir),
        "title": manifest.get("title"),
        "age_band": manifest.get("age_band"),
        "page_count": len(jobs),
        "plan_fingerprint": plan_fingerprint,
        "character_reference_path": next(iter(character_paths)),
        "character_version": next(iter(character_versions)),
        "jobs": jobs,
    }


def _load_queue(queue_path: Path) -> dict[str, Any]:
    state = _read_json(queue_path)
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported queue schema: {state.get('schema_version')!r}")
    if not isinstance(state.get("jobs"), list):
        raise ValueError("queue jobs must be a list")
    return state


def _save_queue(queue_path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    _write_atomic(queue_path, state)


def _job(state: dict[str, Any], page: int) -> dict[str, Any]:
    for job in state["jobs"]:
        if int(job["page"]) == int(page):
            return job
    raise ValueError(f"page is not in queue: {page}")


def _append_event(state: dict[str, Any], event: str, page: int | None = None, **fields: Any) -> None:
    record = {"event": event, "at": _now(), **fields}
    if page is not None:
        record["page"] = int(page)
    state.setdefault("events", []).append(record)


def _book_path_from_queue(state: dict[str, Any], value: str | Path) -> Path:
    return Path(state["book_dir"]) / value if not Path(value).is_absolute() else Path(value)


def init_queue(
    book_dir: str | Path,
    queue_path: str | Path,
    *,
    max_in_flight: int = DEFAULT_MAX_IN_FLIGHT,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, Any]:
    if max_in_flight < 1 or max_in_flight > 3:
        raise ValueError("max_in_flight must be between 1 and 3")
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    book_dir = Path(book_dir).resolve()
    queue_path = Path(queue_path).resolve()
    planned = _plan(book_dir)
    existing: dict[str, Any] | None = None
    if queue_path.exists():
        existing = _load_queue(queue_path)
        if Path(existing["book_dir"]).resolve() != book_dir:
            raise ValueError("existing queue belongs to a different book directory")

    old_by_page = {int(job["page"]): job for job in existing.get("jobs", [])} if existing else {}
    jobs = []
    for fresh in planned["jobs"]:
        old = old_by_page.get(int(fresh["page"]))
        if old and old.get("base_request_fingerprint") == fresh["base_request_fingerprint"]:
            preserved = copy.deepcopy(old)
            preserved["max_attempts"] = max_attempts
            output = _book_path_from_queue({"book_dir": str(book_dir)}, preserved.get("output_path", ""))
            if preserved.get("status") in DONE_STATUSES:
                if output.is_file() and preserved.get("output_sha256") == _file_hash(output):
                    preserved["status"] = "cached"
                    preserved["updated_at"] = _now()
                    jobs.append(preserved)
                    continue
                preserved["status"] = "pending"
                preserved["output_sha256"] = None
                preserved["last_error"] = "previous output is missing or has changed"
            if preserved.get("status") == "running":
                preserved["status"] = "retryable" if int(preserved.get("attempts", 0)) < max_attempts else "failed"
            jobs.append(preserved)
            continue
        fresh["max_attempts"] = max_attempts
        jobs.append(fresh)

    state = {
        "schema_version": SCHEMA_VERSION,
        "queue_id": existing.get("queue_id") if existing else f"queue-{int(time.time() * 1000)}",
        "book_dir": str(book_dir),
        "title": planned["title"],
        "age_band": planned["age_band"],
        "page_count": planned["page_count"],
        "plan_fingerprint": planned["plan_fingerprint"],
        "character_reference_path": planned["character_reference_path"],
        "character_version": planned["character_version"],
        "max_in_flight": max_in_flight,
        "max_attempts": max_attempts,
        "jobs": jobs,
        "events": copy.deepcopy(existing.get("events", [])) if existing else [],
        "created_at": existing.get("created_at") if existing else _now(),
        "updated_at": _now(),
    }
    _append_event(state, "initialized", plan_fingerprint=planned["plan_fingerprint"], reused=bool(existing))
    _write_atomic(queue_path, state)
    return state


def claim_job(queue_path: str | Path, page: int) -> dict[str, Any]:
    queue_path = Path(queue_path).resolve()
    state = _load_queue(queue_path)
    job = _job(state, page)
    if job["status"] in DONE_STATUSES:
        raise RuntimeError(f"page {page} is already complete; reset it explicitly to regenerate")
    if job["status"] == "failed" and int(job.get("attempts", 0)) >= int(job.get("max_attempts", state["max_attempts"])):
        raise RuntimeError(f"page {page} exhausted its retry budget")
    running = sum(1 for item in state["jobs"] if item["status"] in ACTIVE_STATUSES)
    if running >= int(state["max_in_flight"]):
        raise RuntimeError("max_in_flight reached; complete or fail a running page first")
    job["status"] = "running"
    job["attempts"] = int(job.get("attempts", 0)) + 1
    job["started_at"] = _now()
    job["updated_at"] = _now()
    job["last_error"] = None
    _append_event(state, "claimed", page, attempt=job["attempts"])
    _save_queue(queue_path, state)
    return copy.deepcopy(job)


def claim_batch(queue_path: str | Path, pages: list[int]) -> list[dict[str, Any]]:
    """Atomically claim a bounded page group for host-managed batch generation."""
    queue_path = Path(queue_path).resolve()
    state = _load_queue(queue_path)
    normalized = [int(page) for page in pages]
    if not normalized or len(set(normalized)) != len(normalized):
        raise ValueError("claim batch requires one or more distinct page numbers")
    jobs = [_job(state, page) for page in normalized]
    running = sum(1 for item in state["jobs"] if item["status"] in ACTIVE_STATUSES)
    capacity = int(state["max_in_flight"]) - running
    if len(jobs) > capacity:
        raise RuntimeError(f"batch has {len(jobs)} pages but only {max(capacity, 0)} in-flight slots are available")
    for job in jobs:
        if job["status"] in DONE_STATUSES:
            raise RuntimeError(f"page {job['page']} is already complete; reset it explicitly to regenerate")
        if job["status"] == "failed" and int(job.get("attempts", 0)) >= int(job.get("max_attempts", state["max_attempts"])):
            raise RuntimeError(f"page {job['page']} exhausted its retry budget")
    for job in jobs:
        job["status"] = "running"
        job["attempts"] = int(job.get("attempts", 0)) + 1
        job["started_at"] = _now()
        job["updated_at"] = _now()
        job["last_error"] = None
    _append_event(state, "batch_claimed", pages=normalized, attempts=[job["attempts"] for job in jobs])
    _save_queue(queue_path, state)
    return copy.deepcopy(jobs)


def complete_job(
    queue_path: str | Path,
    page: int,
    output_path: str | Path,
    *,
    elapsed_ms: int | None = None,
) -> dict[str, Any]:
    queue_path = Path(queue_path).resolve()
    state = _load_queue(queue_path)
    job = _job(state, page)
    if job["status"] != "running":
        raise RuntimeError(f"page {page} must be running before completion")
    output = Path(output_path)
    if not output.is_absolute():
        output = Path(state["book_dir"]) / output
    output = output.resolve()
    relative = _relative_to_book(Path(state["book_dir"]), output)
    if not output.is_file():
        raise ValueError(f"completed image does not exist: {output}")
    job.update(
        {
            "status": "completed",
            "output_path": relative,
            "output_sha256": _file_hash(output),
            "elapsed_ms": elapsed_ms,
            "finished_at": _now(),
            "updated_at": _now(),
            "last_error": None,
        }
    )
    _append_event(state, "completed", page, elapsed_ms=elapsed_ms, output_path=relative)
    _save_queue(queue_path, state)
    return copy.deepcopy(job)


def fail_job(queue_path: str | Path, page: int, error: str) -> dict[str, Any]:
    queue_path = Path(queue_path).resolve()
    state = _load_queue(queue_path)
    job = _job(state, page)
    if job["status"] != "running":
        raise RuntimeError(f"page {page} must be running before failure is recorded")
    message = str(error).strip() or "unspecified generation failure"
    job.setdefault("errors", []).append({"at": _now(), "message": message})
    job["last_error"] = message
    job["status"] = "retryable" if int(job.get("attempts", 0)) < int(job.get("max_attempts", state["max_attempts"])) else "failed"
    job["updated_at"] = _now()
    _append_event(state, "failed", page, retryable=job["status"] == "retryable", message=message)
    _save_queue(queue_path, state)
    return copy.deepcopy(job)


def resume_queue(queue_path: str | Path) -> dict[str, Any]:
    queue_path = Path(queue_path).resolve()
    state = _load_queue(queue_path)
    changed = []
    for job in state["jobs"]:
        if job["status"] in ACTIVE_STATUSES:
            job["status"] = "retryable" if int(job.get("attempts", 0)) < int(job.get("max_attempts", state["max_attempts"])) else "failed"
            job["updated_at"] = _now()
            changed.append(int(job["page"]))
    _append_event(state, "resumed", pages=changed)
    _save_queue(queue_path, state)
    return state


def reset_page(queue_path: str | Path, page: int, reason: str) -> dict[str, Any]:
    queue_path = Path(queue_path).resolve()
    state = _load_queue(queue_path)
    job = _job(state, page)
    if job["status"] == "running":
        raise RuntimeError("cannot reset a running page; resume or fail it first")
    old_output = job.get("output_path")
    if old_output and _book_path_from_queue(state, old_output).is_file():
        job["previous_output_path"] = old_output
    job["revision"] = int(job.get("revision", 1)) + 1
    original = Path(job.get("output_path", f"images/page-{int(page):02d}.png"))
    stem = original.stem
    suffix = original.suffix or ".png"
    job["output_path"] = (original.parent / f"{stem}-r{job['revision']}{suffix}").as_posix()
    job["request_fingerprint"] = _canonical_hash(
        {"base": job["base_request_fingerprint"], "revision": job["revision"], "reason": str(reason)}
    )
    job["status"] = "pending"
    job["attempts"] = 0
    job["errors"] = []
    job["last_error"] = None
    job["output_sha256"] = None
    job["elapsed_ms"] = None
    job["updated_at"] = _now()
    _append_event(state, "page_reset", page, reason=str(reason), revision=job["revision"])
    _save_queue(queue_path, state)
    return state


def status(queue_path: str | Path) -> dict[str, Any]:
    state = _load_queue(Path(queue_path).resolve())
    counts = {key: 0 for key in ("pending", "running", "retryable", "failed", "completed", "cached")}
    attempts = 0
    elapsed_ms = 0
    for job in state["jobs"]:
        status_name = str(job.get("status"))
        counts[status_name] = counts.get(status_name, 0) + 1
        attempts += int(job.get("attempts", 0))
        if isinstance(job.get("elapsed_ms"), int):
            elapsed_ms += int(job["elapsed_ms"])
    failures = sum(1 for event in state.get("events", []) if event.get("event") == "failed")
    return {
        "queue_id": state["queue_id"],
        "book_dir": state["book_dir"],
        "page_count": state["page_count"],
        "max_in_flight": state["max_in_flight"],
        "counts": counts,
        "attempts": attempts,
        "failure_events": failures,
        "retry_events": sum(1 for event in state.get("events", []) if event.get("event") == "failed" and event.get("retryable")),
        "recorded_image_elapsed_ms": elapsed_ms,
        "updated_at": state["updated_at"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init", help="validate the complete plan and create/reuse one page job per page")
    init.add_argument("book_dir", type=Path)
    init.add_argument("queue_json", type=Path)
    init.add_argument("--max-in-flight", type=int, default=DEFAULT_MAX_IN_FLIGHT)
    init.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("queue_json", type=Path)
    claim = subparsers.add_parser("claim")
    claim.add_argument("queue_json", type=Path)
    claim.add_argument("--page", type=int, required=True)
    batch = subparsers.add_parser("claim-batch", help="atomically claim a bounded group of pages")
    batch.add_argument("queue_json", type=Path)
    batch.add_argument("--pages", type=int, nargs="+", required=True)
    complete = subparsers.add_parser("complete")
    complete.add_argument("queue_json", type=Path)
    complete.add_argument("--page", type=int, required=True)
    complete.add_argument("--output", type=Path, required=True)
    complete.add_argument("--elapsed-ms", type=int)
    fail = subparsers.add_parser("fail")
    fail.add_argument("queue_json", type=Path)
    fail.add_argument("--page", type=int, required=True)
    fail.add_argument("--error", required=True)
    resume = subparsers.add_parser("resume")
    resume.add_argument("queue_json", type=Path)
    reset = subparsers.add_parser("reset-page")
    reset.add_argument("queue_json", type=Path)
    reset.add_argument("--page", type=int, required=True)
    reset.add_argument("--reason", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "init":
            result = init_queue(args.book_dir, args.queue_json, max_in_flight=args.max_in_flight, max_attempts=args.max_attempts)
        elif args.command == "status":
            result = status(args.queue_json)
        elif args.command == "claim":
            result = claim_job(args.queue_json, args.page)
        elif args.command == "claim-batch":
            result = claim_batch(args.queue_json, args.pages)
        elif args.command == "complete":
            result = complete_job(args.queue_json, args.page, args.output, elapsed_ms=args.elapsed_ms)
        elif args.command == "fail":
            result = fail_job(args.queue_json, args.page, args.error)
        elif args.command == "resume":
            result = resume_queue(args.queue_json)
        elif args.command == "reset-page":
            result = reset_page(args.queue_json, args.page, args.reason)
        else:  # pragma: no cover
            raise ValueError(f"unsupported command: {args.command}")
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

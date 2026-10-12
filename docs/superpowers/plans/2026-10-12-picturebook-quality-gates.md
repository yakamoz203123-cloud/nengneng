# Picturebook Skill Quality Gates Implementation Plan

> Execute with `superpowers:subagent-driven-development`, one independent
> implementer and review per task. Grok Bot work is deferred.

**Goal:** Harden the platform-neutral `make-kids-picturebooks` skill against
the observed empty-PDF, final-font-size, text-image contradiction, character
drift, and page-to-page continuity failures.

**Spec:** `docs/superpowers/specs/2026-10-12-picturebook-quality-gates-design.md`

## Global constraints

- Work only in `make-kids-picturebooks-hardening` worktree.
- Preserve `schema_version: 1` and Python 3.10+ compatibility.
- Do not copy the supplied PDFs or any user assets into the repository.
- Every production change follows TDD: write a focused failing test, run it,
  implement the smallest fix, then run the focused and full suite.
- Do not weaken existing quality thresholds or completion stop conditions.
- Keep Grok adapter tasks out of this iteration.

## Task 1: Add final export quality gates

**Files:** create `scripts/validate_exports.py`; modify `scripts/export_book.py`,
`scripts/accept_book.py`; add `tests/test_validate_exports.py` and focused
export/acceptance tests.

**Produces:** reusable validation of non-empty readable reading/booklet PDFs,
page counts, A5/A4 dimensions, extractable page text, and minimum final print
text size (18 pt default, configurable upward only).

Steps:

1. Add failing tests for zero-byte PDF, malformed PDF, missing page text,
   wrong page count/dimension, and final print text below the threshold.
2. Run only the new tests and confirm expected failures.
3. Implement the validator and call it before export publication and from
   acceptance checks.
4. Add a valid synthetic export test and verify the booklet half-page text is
   extractable.
5. Run focused tests, then commit:
   `feat: gate final picturebook exports`

## Task 2: Add continuity manifest fields and validation

**Files:** modify `assets/page-manifest-template.json`,
`scripts/validate_page_manifest.py`; add tests in `tests/test_page_manifest.py`.

**Produces:** additive continuity records with page-specific errors and
completion-mode checks for `text_image_match` and `continuity_review`.

Steps:

1. Add failing tests for missing/invalid continuity records, incomplete review
   evidence, and incompatible adjacent entry/hook state IDs.
2. Run the focused manifest tests and confirm expected failures.
3. Implement shape/status/adjacency validation without inventing content.
4. Update the template with explicit page-1 and final-page boundary values.
5. Run focused and full manifest tests, then commit:
   `feat: record and validate page continuity`

## Task 3: Strengthen skill guidance and review artifacts

**Files:** modify `SKILL.md`, `references/characters.md`,
`references/composition.md`, `references/page-records.md`, `references/review.md`,
`references/printing.md`, `references/acceptance.md`; add tests for required
workflow wording/links if needed.

**Produces:** clear operational rules for a stable character bible, explicit
per-page reference paths, paired-page review, text-image state matching, and
final-output font checks. Documentation must distinguish deterministic checks
from human visual judgment.

Steps:

1. Add `tests/test_skill_guidance.py` as a documentation contract test for the
   new gates and required reference links; run it red.
2. Update the workflow and references concisely, without duplicating generic
   advice or adding platform-specific syntax.
3. Run the documentation test and full suite; commit:
   `docs: strengthen continuity and visual review workflow`

## Task 4: Package and independently review

1. Run compile checks, full unittest discovery, `quick_validate.py`, package
   creation, and `git diff --check`.
2. Inspect the package contents for one `SKILL.md`, no user assets, and the
   new validator/template/references.
3. Run the final branch review package and have a fresh reviewer check the
   acceptance criteria and failure modes.
4. Fix only critical/important findings with a new failing test first.
5. Update `RELEASE.md` with the quality-gate iteration and its deferred Grok
   work. Commit:
   `chore: package picturebook quality gates`

## Completion command

```text
python -X utf8 -m compileall make-kids-picturebooks/scripts
python -X utf8 -W error::DeprecationWarning -m unittest discover -s make-kids-picturebooks/tests -q
python -X utf8 "C:/Users/Windows/.codex/skills/.system/skill-creator/scripts/quick_validate.py" make-kids-picturebooks
python -X utf8 make-kids-picturebooks/scripts/package_skill.py make-kids-picturebooks dist/make-kids-picturebooks-v0.9.2.zip --version 0.9.2
git diff --check
```

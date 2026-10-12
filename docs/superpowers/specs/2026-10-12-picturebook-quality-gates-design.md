# Picturebook Skill Quality Gates Design

## Goal

Make `make-kids-picturebooks` reliable enough for a second real generation
attempt by turning the observed PDF failures into deterministic gates and a
repeatable continuity review. Platform adapters, including Grok Bot, are
explicitly deferred until the platform-neutral skill is stable.

## Evidence and root causes

- The supplied `reading.pdf` was empty, so it could not be opened or reviewed.
- The supplied booklet PDF was readable, but its story text was about 12 pt in
  the final file, and one page stated that the box was empty while its image
  still showed two stars.
- The current export flow records a minimum text size but does not fail when a
  final output is empty, unreadable, missing extractable text, or too small
  after imposition.
- The current page manifest records per-page props but not the previous-page
  state, the current page's entry state, or the next-page hook. Continuity is
  therefore advisory rather than checkable.
- Character guidance and layout guidance are already present, but the core
  workflow does not require a stable reference path, paired-page review, or a
  final print-size check.

## Design

### 1. Final output quality gate

Add a small reusable export validator used by `export_book.py` and acceptance
checks. It must verify that both PDFs exist, are non-empty and readable, have
the expected page counts and dimensions, and contain the expected page text.
It must measure extracted final text spans rather than trusting source layout
settings. The default print threshold is 18 pt; the layout may raise this
threshold but may not lower it. A zero-byte or malformed PDF must fail before
the destination export directory is published.

The booklet remains derived from the validated reading PDF. The validator must
not silently repair an empty source or invent missing text.

### 2. Continuity records

Keep `schema_version: 1` and make the new fields additive. Each page record
may carry:

- `previous_page_state`, `current_page_entry`, and `next_page_hook`: objects
  with a non-empty stable `state_id` and a concise `summary`. Page 1 uses
  `story_start` for the previous state and the last page uses `story_end` for
  the next hook. The validator compares the previous page's hook `state_id`
  with the next page's entry `state_id`.
- `text_image_match` and `continuity_review`: objects with `status` set to
  `pending`, `passed`, or `failed`, plus an `evidence` string. Completion mode
  requires `passed` and non-empty evidence.

The validator checks shape, allowed statuses, non-empty evidence in completion
mode, and adjacent-page agreement: page N's `next_page_hook` must be compatible
with page N+1's `current_page_entry` when both are declared. It does not claim
to judge literary quality automatically; the evidence fields preserve the
human/model review decision.

### 3. Character and layout workflow

Require a declared character reference path for every page once a project has
approved character assets. Add explicit workflow instructions to keep a stable
character bible, lock identity anchors, review adjacent pages as pairs, and
vary text areas according to scene composition. Preserve the rule that a
generated image is not complete until the actual page is viewed with editable
text overlaid.

### 4. Scope and safety

- No Grok adapter, platform-specific prompt, or new schema version in this
  iteration.
- No user PDF, child data, character image, or generated book is copied into
  the public skill repository.
- Validators report defects; they do not rewrite source text, images, or PDFs.

## Acceptance criteria

1. Empty, malformed, wrong-page-count, wrong-dimension, and too-small final
   PDFs fail deterministic tests.
2. A valid synthetic export passes and its booklet text is still extractable on
   both imposed halves.
3. Continuity fields validate in planning mode and become required for digital
   completion when present in the project manifest.
4. A deliberately contradictory adjacent-page fixture fails with a useful
   page-specific message.
5. The skill documents stable character references, text-image state checks,
   and paired-page review without claiming automatic visual identity proof.
6. The full existing suite, new focused tests, package validation, and static
   checks pass before publication.

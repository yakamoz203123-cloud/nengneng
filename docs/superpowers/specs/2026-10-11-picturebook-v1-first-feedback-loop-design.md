# Picturebook v1 First Feedback Loop Design

## Goal

Make the `make-kids-picturebooks` Skill usable as a repeatable cross-platform workflow by adding a Grok Bot adapter, a separately runnable behavior-evaluation registry, and a gated 5–7-year-old sample-book intake path.

## Current evidence

- The v0.9.1 package is published and the deterministic Python suite is green.
- The existing behavior baseline exposed two important risks: false activation for layout-only requests and false completion under print pressure.
- The updated behavior run is not yet evidence because the available runner exhausted its allowance; no result file will be fabricated.
- The published Skill is Codex-oriented. Grok Bot has its own saved-Skill and `/` invocation workflow, so platform instructions must remain an adapter instead of being mixed into the core workflow.

## Design

### 1. Platform-neutral core

Keep `SKILL.md`, references, scripts, and project gates as the source of truth for adaptation safety, age selection, provenance, approvals, and acceptance. Do not add Grok-specific invocation syntax to the core Skill description.

### 2. Grok Bot adapter

Add a small adapter under `adapters/grok-bot/` containing:

- setup steps for a public GitHub repository or attached Markdown files;
- a bootstrap prompt that asks Grok Bot to save a reusable Skill named “宝宝知识绘本”;
- six smoke prompts covering direct use, indirect use, missing age/source, negative control, and false-completion pressure;
- explicit warnings that `$make-kids-picturebooks` is Codex syntax and `/` is Grok Bot syntax.

The adapter will not claim that Grok has image-generation or PDF-export capability. It will require the Bot to report unavailable capabilities and stop at the corresponding gate.

### 3. Separate behavior registry

Generalize `check_eval_results.py` so callers can pass an alternate prompt registry while preserving the current default. Add a Grok-specific CSV registry and a results template. Templates are not evidence; a real result file is created only after a Grok Bot run.

### 4. Sample-book gate

Add a committed sample intake scaffold for the existing bee-pollination 5–7 prompt. It will be marked `demo-scaffold`, not complete. The scaffold records the source excerpt, concept-card fields, required approvals, and acceptance artifacts needed before a real sample can be called finished.

## Non-goals

- No Schema v2 or migration tool in this iteration.
- No automatic image-generation or PDF service integration.
- No user book, child data, character reference, or generated project asset in the public repository.
- No fabricated Grok evaluation results or claim that a text prompt is a real illustration.

## Acceptance criteria

1. Grok adapter docs are self-contained, use the public repository URL, distinguish Codex and Grok invocation, and preserve all stop conditions.
2. The evaluator accepts the existing registry unchanged and accepts the new Grok registry through an explicit `--prompts` option.
3. The Grok smoke registry has six cases and covers every scoring metric without weakening thresholds.
4. The sample scaffold cannot be mistaken for a completed book: it explicitly requires real illustrations, page evidence, PDF export, and acceptance records.
5. Focused tests and the full existing suite pass before publishing the updated package.


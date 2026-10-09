# Life Model Writing Completion Design

## 1. Purpose

Complete `life-model-writing` as a reliable, reusable Codex Skill that turns everyday social and behavioral questions into evidence-aware Chinese spoken scripts. The completion work must preserve the existing product boundary: this Skill produces copy, not video, and it does not become a general theory encyclopedia, crawler, or high-risk professional adviser.

The first release target is a public experimental version, not a stable release.

## 2. Current Baseline

The repository already contains:

- A focused `SKILL.md` with problem modeling, theory competition, mechanism reasoning, boundary checks, and spoken-script conversion.
- Eight composite theory cards and four writing/quality references.
- Twelve content evaluation prompts plus historical baseline and GREEN records.
- A usable explicit-invocation behavior demonstrated by ten audit cases.

The audit identified four blocking gaps:

1. No executable, independent, reproducible evaluation loop.
2. Important theories used by the base model are absent from the packaged knowledge base.
3. Cross-disciplinary reasoning usually places theories side by side instead of connecting them through shared variables and predictions.
4. The repository lacks the installation, licensing, documentation, and CI assets required for an experimental open-source release.

The detailed audit is stored outside the project at:

`C:\Users\Windows\Documents\ChatGPT\文案skill-audit-2026-10-09\CROSS_DISCIPLINARY_SKILL_AUDIT_2026-10-09.md`

## 3. Scope

### 3.1 Included

- A standard-library-only offline evaluation toolchain.
- Machine-readable content, activation, negative, incomplete-input, and edge-case evaluations.
- Immutable raw-output import and separate deterministic/manual scoring.
- Six additional theory cards with source and boundary requirements.
- A theory-selection and theory-integration protocol in `SKILL.md`.
- Experimental-release documentation, licensing, installation guidance, version history, and CI validation.
- Fresh-environment installation and discovery checks.

### 3.2 Excluded

- Paid or automatic model API calls in the first implementation.
- Video production, voice synthesis, image generation, or editing.
- Web crawling, live databases, or automatic factual research.
- Multiple persona packs or marketing-title generators.
- Medical, legal, or investment decision support.
- Claims of stable-release quality.

## 4. Architecture

The completion work uses four layers.

### 4.1 Static validation layer

`scripts/validate_skill.py` validates the repository without third-party dependencies. It checks:

- `SKILL.md` frontmatter and required fields.
- Internal Markdown links.
- Theory-card required sections.
- Evaluation JSON schemas.
- Unfinished scaffold markers.
- Consistency between registered theory cards and Skill routing references.

The validator must run on Windows, macOS, and Linux using Python's standard library. It replaces the current unreproducible dependency on a PyYAML-based external validator for project CI, while remaining compatible with running the official validator when its dependencies are present.

### 4.2 Evaluation artifact layer

Evaluation runs use this layout:

```text
evals/runs/<run-id>/
├── manifest.json
├── outputs/
│   └── <case-id>.md
├── checks/
│   └── <case-id>.json
├── scores/
│   └── <case-id>.json
└── summary.json
```

`evals/runs/` is ignored by Git. Selected reviewed runs may be copied to `evals/baselines/` as versioned evidence.

The manifest records:

- Run identifier and timestamps.
- Git commit or `unknown`.
- Model name, backend version, and parameters, each allowing `unknown`.
- Invocation mode: explicit, implicit, manual import, or other declared mode.
- Human intervention.
- Case-set versions.
- Errors and skipped cases.

Imported raw outputs are immutable inputs to later checks and scoring. Scoring scripts must never rewrite them.

### 4.3 Scoring layer

Scoring is split into two independent classes.

Deterministic checks cover only observable invariants such as:

- Output exists and is readable.
- One requested version is present unless multiple versions were requested.
- Length falls within the selected output contract.
- Required run metadata exists.
- Disallowed absolute claims and boundary language are flagged for review.
- Score files use valid dimensions and ranges.

Deterministic checks must not claim to establish theoretical correctness from keyword matches.

Manual or independent-model rubric scoring covers six dimensions from 0 to 5:

1. Theory-selection accuracy.
2. Causal-reasoning rigor.
3. Cross-disciplinary integration.
4. Spoken-language naturalness.
5. Content completeness.
6. Factual accuracy and boundary awareness.

A case passes only when:

- Total score is at least 24/30.
- Theory selection, causal reasoning, and factual/boundary awareness are each at least 4/5.
- No critical error is recorded for severe theory misuse, fabricated research, unsupported causality, or group stigmatization.

Missing output or missing independent scores produces `unverified`, not a numerical zero. A generator's self-score may be retained as supplemental metadata but cannot be the final score.

### 4.4 Skill capability layer

Only after a reproducible baseline exists will the Skill instructions and knowledge base change. Every behavioral change is compared against the same cases and rubric.

## 5. Files and Responsibilities

```text
life-model-writing/
├── SKILL.md
├── scripts/
│   ├── validate_skill.py
│   ├── create_eval_run.py
│   ├── import_outputs.py
│   └── score_eval_run.py
├── evals/
│   ├── evals.json
│   ├── real-cases.json
│   ├── activation-cases.json
│   ├── rubric.json
│   ├── baselines/
│   └── runs/
├── tests/
│   ├── test_validate_skill.py
│   ├── test_eval_schema.py
│   ├── test_import_outputs.py
│   └── test_score_eval_run.py
└── references/
```

The existing positive evaluation set remains intact. `real-cases.json` contains the ten audit topics. `activation-cases.json` covers direct, indirect, incomplete, negative, and edge activation requests. `rubric.json` is the single source of scoring dimensions and pass thresholds.

## 6. Evaluation Data Flow

1. Select one or more versioned case sets.
2. Create a run directory and manifest.
3. Generate outputs manually through Codex or another declared model environment.
4. Import outputs without modifying their contents.
5. Run deterministic checks.
6. Collect independent rubric scores.
7. Validate score completeness and ranges.
8. Produce a summary with pass, fail, skipped, and unverified counts.
9. Compare the summary with a reviewed baseline.

The first implementation does not call a model. This keeps evaluation free of API keys, automatic charges, and provider lock-in. A future model-runner adapter may be added without changing the artifact or scoring formats.

## 7. Theory Library Completion

Six focused cards will be added:

1. Information asymmetry, signaling, and screening.
2. Search theory, stopping rules, and matching.
3. Coordination games, local optima, and system bottlenecks.
4. Time preference, immediate rewards, and attention competition.
5. Stocks, flows, capacity, and conservation constraints.
6. Diffusion, thresholds, and network propagation.

Each new and existing card must include its current core sections plus:

- Candidate-selection criteria.
- Exclusion conditions.
- Observable predictions.
- Compatible theories.
- Connection variables used in a combined model.

Sources must directly support the card's core claims. A general topic page or researcher profile is not sufficient evidence for a specific mechanism.

Physical concepts require an explicit social-mechanism bridge. Terms such as entropy, quantum behavior, energy, or inertia must not be used as explanations of human behavior unless variables, mechanism, scope, and observable predictions are defined. Superficial metaphor is rejected.

## 8. Theory Selection and Integration

`SKILL.md` will preserve its concise entry role and add a selection contract rather than embedding all theory details.

For each problem, the internal analysis must:

1. Generate at least two plausible candidates when the problem supports modeling.
2. Compare mechanism fit, observable variables, assumption cost, prediction value, boundary clarity, and redundancy.
3. Identify a primary model, optional supporting model, and at least one rejected candidate with a reason.
4. Mark any theory not supported by a packaged card as external model knowledge.
5. When combining theories, name the connection variable and explain how one model changes the conditions of the other.
6. Produce at least one conditional prediction that would differ from a single-theory explanation.

Theory names remain absent from the final script when they do not improve the explanation.

## 9. Spoken-Script Contracts

The Skill supports three requested lengths:

- Short: 400-600 Chinese characters.
- Standard: 800-1200 Chinese characters.
- Long: 1500-2200 Chinese characters.

Standard is the default when the user does not specify length. These are quality targets rather than reasons to pad weak material. When evidence or mechanism does not support the requested length, the Skill should remain concise and state the limitation when relevant.

The reasoning structure remains stable, but final prose should vary its presentation. Evaluation flags repeated scaffolding such as mechanically using “first model”, “second model”, and “the mechanism is” in every script. Structure serves reasoning and must not become a visible template.

## 10. Error Handling

- Invalid case-set JSON: stop creation of that run and report the file and field path.
- Missing output: mark the case `unverified`; continue other cases.
- Invalid or incomplete score: exclude that case from aggregate scoring and report the validation error.
- Git metadata unavailable: record `unknown`; do not block offline use.
- Missing theory-card section or broken internal link: fail static validation.
- Historical result lacking its referenced script, environment, or dependency: label it historical and not currently reproduced.
- Existing files in a run directory: refuse overwrite unless the user supplies a new run identifier.

Errors must not delete or rewrite user outputs.

## 11. Testing Strategy

Implementation follows test-first development.

Unit tests cover:

- Valid and invalid frontmatter.
- Broken links and missing theory sections.
- Valid and malformed case sets.
- Run creation and collision refusal.
- Byte-preserving output import.
- Missing outputs.
- Valid, incomplete, and out-of-range scores.
- Summary arithmetic and `unverified` handling.
- Windows and POSIX-style path input where applicable.

Behavioral evaluation covers:

- The existing 12 positive topics.
- The 10 audit topics.
- At least 10 activation cases spanning direct, indirect, incomplete, negative, and edge requests.
- At least two runs for release evidence.
- Independent scoring for release evidence.

Static tests passing does not imply content quality. Engineering checks and behavioral scores are reported separately.

## 12. Open-Source Experimental Packaging

The experimental release adds only packaging assets with direct user value:

- `README.md`: purpose, boundaries, installation, invocation, examples, architecture, evaluation method, current results, and known limitations.
- Repository-root `LICENSE`: Apache License 2.0, covering the Skill instructions, references, evaluation assets, and scripts while retaining notices required by cited sources.
- `CHANGELOG.md`: versioned behavioral and knowledge changes.
- `CONTRIBUTING.md`: card-source and evaluation-evidence requirements.
- `requirements-dev.txt`: empty or minimal declared development dependencies; standard-library-only scripts remain the target.
- `.github/workflows/validate.yml`: static validation and unit tests.

Installation documentation will cover one canonical method and distinguish it from repository-scoped use. A fresh environment must be able to install, discover, and explicitly invoke the Skill by following the README.

## 13. Acceptance Criteria

### 13.1 Evaluation milestone

- All unit tests pass using a documented command.
- Static validation runs with one command and no third-party package.
- The 12 existing cases, 10 audit cases, and at least 10 activation cases validate against their schemas.
- The ten audit outputs import byte-for-byte and produce a valid summary.
- Raw outputs and scores remain separate.
- No API key or paid call is required.

### 13.2 Theory milestone

- Six new cards have direct sources, boundaries, predictions, and integration fields.
- Existing cards receive the same selection/integration fields where applicable.
- At least five reviewed cases produce a connected-model prediction not available from either theory alone.
- No accepted case uses physical metaphor as a causal explanation without a bridge mechanism.
- Existing reviewed cases do not regress below their release thresholds.

### 13.3 Experimental-release milestone

- Repository-root README, Apache-2.0 LICENSE, changelog, contribution guide, and CI are present.
- A clean environment can install and discover the Skill using the documented path.
- Three smoke cases run after installation.
- CI validates frontmatter, links, case schemas, theory-card structure, and unit tests.
- The release is labeled experimental and lists known limitations.

## 14. Delivery Sequence

1. Build and test the offline evaluation loop without changing Skill behavior.
2. Import the audit cases and establish a reviewed baseline.
3. Add theory cards and update selection/integration instructions one focused change at a time.
4. Re-run the same evaluation set after each behavioral change.
5. Add open-source packaging and CI.
6. Verify installation and discovery in a clean environment.

No theory expansion or packaging claim is accepted without the corresponding evaluation evidence.

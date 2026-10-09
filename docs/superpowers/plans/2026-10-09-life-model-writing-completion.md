# Life Model Writing Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `life-model-writing` from a prompt-and-reference prototype into a reproducibly evaluated, theory-grounded, installable Codex Skill suitable for an experimental GitHub release.

**Architecture:** Build a standard-library-only offline evaluation pipeline before changing Skill behavior. Establish a versioned baseline, then expand and connect the theory library, update the Skill contract, and finally add open-source packaging and clean-environment verification. Raw model outputs, deterministic checks, and independent rubric scores remain separate artifacts.

**Tech Stack:** Python 3.11+ standard library (`argparse`, `hashlib`, `json`, `pathlib`, `re`, `shutil`, `subprocess`, `unittest`), Markdown, JSON, YAML metadata, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-09-life-model-writing-completion-design.md`

## Global Constraints

- The Skill produces written copy only; do not add video, audio, image, or editing functions.
- The first evaluator must not call a model API, require an API key, install third-party packages, or incur paid usage.
- Preserve the existing 12 evaluation cases; extend them through separate versioned files.
- Treat missing outputs or independent scores as `unverified`, never as a numerical zero or a pass.
- Never rewrite imported raw outputs; store and verify their SHA-256 digest.
- Keep deterministic checks separate from judgments about theory, causality, factual correctness, and prose quality.
- Keep `SKILL.md` concise and route detail to references.
- Use Apache License 2.0 for the repository release.
- Preserve the pre-existing untracked `wechat-group-silence-v1/` directory and exclude it from all commits.
- Use `apply_patch` for source and documentation edits.

## Review Focus

- A malformed or partially valid case-set file must fail with the source file and JSON field path, without creating a partial run.
- A duplicate run identifier or output identifier must refuse overwrite and preserve the existing bytes.
- Missing output, missing independent score, and an explicit failing score must remain three distinct states in summaries.
- Activation cases that should not invoke this Skill—including generic copywriting and medical/legal/investment advice—must be represented and reported separately from content quality.
- Physical or systems analogies must identify measurable variables and a bridge mechanism; superficial entropy, quantum, energy, and inertia metaphors must fail review.

---

### Task 1: Shared evaluation schema and loader

**Files:**
- Create: `life-model-writing/scripts/eval_common.py`
- Create: `life-model-writing/tests/__init__.py`
- Create: `life-model-writing/tests/test_eval_schema.py`
- Create: `life-model-writing/tests/fixtures/valid-content-cases.json`
- Create: `life-model-writing/tests/fixtures/invalid-content-cases.json`

**Interfaces:**
- Produces: `EvaluationDataError(ValueError)` with `source` and `field_path` attributes.
- Produces: `read_json(path: Path) -> dict[str, object]`.
- Produces: `validate_case_set(data: dict[str, object], source: str) -> list[dict[str, object]]`.
- Produces: `load_case_sets(paths: list[Path]) -> list[dict[str, object]]`.
- Produces: `normalize_case_id(value: str | int) -> str`.
- Case IDs are unique after string normalization; existing integer IDs remain compatible.
- Because the Skill folder contains a hyphen and is not a Python package, tests prepend `life-model-writing/scripts` to `sys.path` and import script modules by filename; production scripts use sibling imports from that same directory.

- [ ] **Step 1: Write failing loader tests**

Add `unittest.TestCase` tests that assert:

```python
def test_existing_case_shape_normalizes_integer_ids(self):
    cases = validate_case_set(existing_shape, "evals.json")
    self.assertEqual(cases[0]["id"], "1")

def test_duplicate_ids_across_case_sets_fail(self):
    with self.assertRaises(EvaluationDataError) as error:
        load_case_sets([first_path, duplicate_path])
    self.assertEqual(error.exception.field_path, "evals[0].id")

def test_invalid_case_reports_source_and_field_path(self):
    with self.assertRaises(EvaluationDataError) as error:
        validate_case_set(invalid_data, "invalid.json")
    self.assertEqual(error.exception.source, "invalid.json")
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_eval_schema.py" -v
```

Expected: import failure because `scripts/eval_common.py` does not exist.

- [ ] **Step 3: Implement the minimal schema loader**

Support the existing top-level `skill_name`, `version`, and `evals` list. Normalize each case to these fields:

```python
{
    "id": str,
    "name": str,
    "kind": "content" | "activation",
    "prompt": str,
    "expected_output": str,
    "assertions": list[str],
    "length_contract": "short" | "standard" | "long" | None,
    "expected_activation": bool | None,
    "source": str,
}
```

Existing cases default to `kind="content"`; optional fields default to `None`. Reject empty prompts, invalid kinds, empty assertions, and duplicate normalized IDs.

- [ ] **Step 4: Run focused and full tests**

Run:

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_eval_schema.py" -v
python -m unittest discover -s life-model-writing/tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add -- life-model-writing/scripts/eval_common.py life-model-writing/tests
git commit -m "test: add evaluation schema loader"
```

### Task 2: Dependency-free static Skill validator

**Files:**
- Create: `life-model-writing/scripts/validate_skill.py`
- Create: `life-model-writing/tests/test_validate_skill.py`
- Create: `life-model-writing/tests/fixtures/invalid-skill/`

**Interfaces:**
- Consumes: `load_case_sets()` from Task 1.
- Produces: `parse_frontmatter(text: str) -> dict[str, str]` for flat `name` and `description` fields only.
- Produces: `validate_skill_root(skill_root: Path) -> list[str]`, where an empty list means valid.
- CLI: `python life-model-writing/scripts/validate_skill.py life-model-writing`; exit 0 on success, 1 on validation errors, 2 on usage/runtime errors.

- [ ] **Step 1: Write failing validation tests**

Cover valid frontmatter, missing description, invalid name, broken relative Markdown links, missing theory sections, invalid evaluation JSON, unfinished scaffold markers, and a Skill route pointing to a missing theory card.

Required theory headings:

```python
CORE_HEADINGS = {
    "一句话定义", "它解释什么", "最小模型", "关键变量", "推演步骤",
    "适合解释的生活问题", "不适合解释的生活问题", "常见误用",
    "最小例子", "事实与证据边界", "可靠来源",
}
```

Selection headings are introduced as required in Task 7, not before.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_validate_skill.py" -v
```

Expected: import failure for `validate_skill`.

- [ ] **Step 3: Implement validator**

Use `pathlib` and `re`; do not import PyYAML. Parse only the flat frontmatter fields this Skill requires. Report every discovered error in a stable `path: message` form instead of stopping at the first one.

- [ ] **Step 4: Verify current project**

```powershell
python life-model-writing/scripts/validate_skill.py life-model-writing
python -m unittest discover -s life-model-writing/tests -v
```

Expected: `VALIDATION=PASS` and all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add -- life-model-writing/scripts/validate_skill.py life-model-writing/tests/test_validate_skill.py life-model-writing/tests/fixtures/invalid-skill
git commit -m "feat: add dependency-free skill validation"
```

### Task 3: Reproducible evaluation-run creation

**Files:**
- Create: `life-model-writing/scripts/create_eval_run.py`
- Create: `life-model-writing/tests/test_create_eval_run.py`
- Modify: `life-model-writing/scripts/eval_common.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `create_run(skill_root: Path, case_paths: list[Path], run_id: str, model: dict[str, object], invocation_mode: str, human_intervention: str, now: datetime | None = None) -> Path`.
- CLI requires `--skill-root`, one or more `--cases`, `--run-id`, `--model-name`, `--invocation-mode`, and `--human-intervention`; backend version and parameters may be `unknown`.
- Manifest cases contain ID, source, kind, prompt digest, length contract, and expected activation.

- [ ] **Step 1: Write failing run-creation tests**

Assert that a run creates `manifest.json`, `outputs/`, `checks/`, and `scores/`; timestamps can be injected; Git metadata may become `unknown`; invalid cases create no directory; duplicate run IDs preserve the original manifest and raise `FileExistsError`.

- [ ] **Step 2: Run RED test**

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_create_eval_run.py" -v
```

- [ ] **Step 3: Implement run creation**

Validate all inputs before creating directories. Write JSON as UTF-8 with `ensure_ascii=False`, sorted keys, and a trailing newline. Resolve Git HEAD with a non-mutating subprocess call and fall back to `unknown`.

- [ ] **Step 4: Ignore local runs**

Append only this repository-relative rule:

```gitignore
life-model-writing/evals/runs/
```

- [ ] **Step 5: Verify**

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_create_eval_run.py" -v
python -m unittest discover -s life-model-writing/tests -v
```

- [ ] **Step 6: Commit**

```powershell
git add -- .gitignore life-model-writing/scripts/create_eval_run.py life-model-writing/scripts/eval_common.py life-model-writing/tests/test_create_eval_run.py
git commit -m "feat: create reproducible evaluation runs"
```

### Task 4: Immutable output import

**Files:**
- Create: `life-model-writing/scripts/import_outputs.py`
- Create: `life-model-writing/tests/test_import_outputs.py`

**Interfaces:**
- Produces: `import_output(run_dir: Path, case_id: str, source: Path) -> dict[str, object]`.
- Produces: `import_output_directory(run_dir: Path, source_dir: Path) -> list[dict[str, object]]`.
- Output filenames use normalized case IDs from the manifest.
- Import record includes source filename, byte length, SHA-256, and import timestamp in `manifest.json`.

- [ ] **Step 1: Write failing import tests**

Test byte-for-byte preservation with Chinese UTF-8 text and CRLF bytes, unknown case rejection, duplicate output refusal, directory import, and continuation when another expected case has no source file.

```python
source_bytes = b"\xe4\xb8\xad\xe6\x96\x87\r\n"
self.assertEqual(imported_path.read_bytes(), source_bytes)
self.assertEqual(record["sha256"], hashlib.sha256(source_bytes).hexdigest())
```

- [ ] **Step 2: Run RED test**

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_import_outputs.py" -v
```

- [ ] **Step 3: Implement immutable import**

Read and write bytes, use exclusive creation, and update the manifest only after the copied bytes and digest have been verified. Do not normalize line endings.

- [ ] **Step 4: Verify**

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_import_outputs.py" -v
python -m unittest discover -s life-model-writing/tests -v
```

- [ ] **Step 5: Commit**

```powershell
git add -- life-model-writing/scripts/import_outputs.py life-model-writing/tests/test_import_outputs.py
git commit -m "feat: import evaluation outputs immutably"
```

### Task 5: Deterministic checks and independent score aggregation

**Files:**
- Create: `life-model-writing/evals/rubric.json`
- Create: `life-model-writing/scripts/score_eval_run.py`
- Create: `life-model-writing/tests/test_score_eval_run.py`

**Interfaces:**
- Produces: `count_non_whitespace_characters(text: str) -> int`.
- Produces: `check_output(case: dict[str, object], output_path: Path) -> dict[str, object]`.
- Produces: `validate_score(score: dict[str, object], rubric: dict[str, object], case_id: str) -> dict[str, object]`.
- Produces: `summarize_run(run_dir: Path, rubric_path: Path) -> dict[str, object]`.
- CLI: `python life-model-writing/scripts/score_eval_run.py --run-dir <dir> --rubric life-model-writing/evals/rubric.json`.

- [ ] **Step 1: Write failing rubric and summary tests**

Test the six exact dimensions, 0-5 range, total calculation, critical floors, critical errors, missing output, missing score, self-score with `independent=false`, explicit failure, and mixed summaries.

Expected status rules:

```python
missing_output == "unverified"
missing_independent_score == "unverified"
independent_total_below_24 == "fail"
critical_dimension_below_4 == "fail"
critical_error_present == "fail"
all_thresholds_met == "pass"
```

- [ ] **Step 2: Run RED test**

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_score_eval_run.py" -v
```

- [ ] **Step 3: Add rubric**

Define IDs:

```text
theory_selection
causal_reasoning
cross_disciplinary_integration
spoken_naturalness
content_completeness
factual_accuracy_and_boundaries
```

Set total threshold 24 and critical floor 4 for theory selection, causal reasoning, and factual accuracy/boundaries. Define critical errors: `severe_theory_misuse`, `fabricated_research`, `unsupported_causality`, `group_stigmatization`.

- [ ] **Step 4: Implement checks and aggregation**

Deterministic checks report `pass`, `fail`, or `review` per observable condition. Absolute-language, missing-boundary-language, and multiple-version patterns are review flags only. They must not change the rubric score automatically.

- [ ] **Step 5: Verify**

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_score_eval_run.py" -v
python -m unittest discover -s life-model-writing/tests -v
python life-model-writing/scripts/validate_skill.py life-model-writing
```

- [ ] **Step 6: Commit**

```powershell
git add -- life-model-writing/evals/rubric.json life-model-writing/scripts/score_eval_run.py life-model-writing/tests/test_score_eval_run.py
git commit -m "feat: score offline evaluation artifacts"
```

### Task 6: Versioned case sets and audited baseline

**Files:**
- Create: `life-model-writing/evals/real-cases.json`
- Create: `life-model-writing/evals/activation-cases.json`
- Create: `life-model-writing/evals/baselines/audit-2026-10-09/manifest.json`
- Create: `life-model-writing/evals/baselines/audit-2026-10-09/outputs/real-01.md` through `real-10.md`
- Create: `life-model-writing/evals/baselines/audit-2026-10-09/checks/real-01.json` through `real-10.json`
- Create: `life-model-writing/evals/baselines/audit-2026-10-09/scores/real-01.json` through `real-10.json`
- Create: `life-model-writing/evals/baselines/audit-2026-10-09/summary.json`
- Modify: `life-model-writing/tests/test_eval_schema.py`

**Interfaces:**
- Consumes: all Task 1-5 interfaces.
- `real-cases.json` uses IDs `real-01` through `real-10` and the exact ten audited prompts.
- `activation-cases.json` contains at least 12 cases: two direct, two indirect, three incomplete, three negative, and two edge cases.
- Baseline self-scores retain `independent=false`; they remain `unverified` until a separate evaluator writes independent scores.

- [ ] **Step 1: Add failing corpus tests**

Assert exact case counts, unique IDs across all three files, complete activation category coverage, both expected activation values, and all content cases carrying a length contract.

- [ ] **Step 2: Run RED test**

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_eval_schema.py" -v
```

- [ ] **Step 3: Add the two case sets**

Preserve the user-supplied prompt wording. Negative cases must include generic slogan copy, video generation, medical diagnosis, legal advice, and investment recommendation; those high-risk examples expect no activation or a boundary response as specified by the case.

- [ ] **Step 4: Import the ten audit outputs**

Extract each complete output from the external audit artifact without rewriting it. Create a temporary run under `evals/runs/audit-2026-10-09` through the public run/import/score interfaces rather than hand-authoring generated metadata. After digest and summary verification, copy that immutable run to `evals/baselines/audit-2026-10-09`. Record the exact model information as exposed and use `unknown` elsewhere.

- [ ] **Step 5: Verify baseline integrity**

```powershell
python life-model-writing/scripts/validate_skill.py life-model-writing
python -m unittest discover -s life-model-writing/tests -v
python life-model-writing/scripts/score_eval_run.py --run-dir life-model-writing/evals/baselines/audit-2026-10-09 --rubric life-model-writing/evals/rubric.json
```

Expected: 10 outputs imported; deterministic checks complete; final content status remains `unverified` until independent scores exist.

- [ ] **Step 6: Commit**

```powershell
git add -- life-model-writing/evals/real-cases.json life-model-writing/evals/activation-cases.json life-model-writing/evals/baselines/audit-2026-10-09 life-model-writing/tests/test_eval_schema.py
git commit -m "test: add real and activation evaluation corpora"
```

### Task 7: Theory-card selection and integration contract

**Files:**
- Create: `life-model-writing/references/theory-09-information-asymmetry-signaling-screening.md`
- Create: `life-model-writing/references/theory-10-search-stopping-matching.md`
- Create: `life-model-writing/references/theory-11-coordination-local-optima-bottlenecks.md`
- Create: `life-model-writing/references/theory-12-time-preference-attention.md`
- Create: `life-model-writing/references/theory-13-stocks-flows-capacity.md`
- Create: `life-model-writing/references/theory-14-diffusion-thresholds-propagation.md`
- Modify: `life-model-writing/references/theory-01-incentives-opportunity-cost.md` through `theory-08-networks-tipping-points-emergence.md`
- Modify: `life-model-writing/scripts/validate_skill.py`
- Modify: `life-model-writing/tests/test_validate_skill.py`

**Interfaces:**
- Every numbered theory card must add headings: `候选理论评分`, `排除条件`, `可观察预测`, `可联合理论`, `连接变量`.
- Every card must contain at least two direct authoritative or primary source links.
- Physical/system cards must include `社会机制桥接` and explicitly reject ungrounded entropy, quantum, energy, and inertia metaphors.

- [ ] **Step 1: Tighten validator tests and verify RED**

Require 14 consecutively numbered cards, the five selection/integration headings on all cards, direct source links, and `社会机制桥接` on cards 13 and 14.

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_validate_skill.py" -v
```

Expected: failure because cards 09-14 and new headings do not exist.

- [ ] **Step 2: Research and create cards 09-12**

Use primary research or official university/encyclopedia sources and verify that each source directly supports the linked mechanism. Target foundational sources include Akerlof/Spence for information and signaling, McCall/Gale-Shapley for search and matching, primary coordination-game or operations-flow sources for coordination and bottlenecks, and Laibson/Simon for time preference and attention scarcity. Do not cite a profile page as mechanism evidence.

- [ ] **Step 3: Research and create cards 13-14**

Use system-dynamics stock/flow sources and primary threshold/cascade research such as Granovetter and Watts. Distinguish accounting constraints and network diffusion models from literal claims about human psychology.

- [ ] **Step 4: Extend cards 01-08**

Add the same five selection/integration fields without rewriting their established definitions. Replace any source that does not directly support a core claim; preserve valid existing links.

- [ ] **Step 5: Run validation and tests**

```powershell
python life-model-writing/scripts/validate_skill.py life-model-writing
python -m unittest discover -s life-model-writing/tests -v
```

Expected: all 14 cards pass structure and link checks.

- [ ] **Step 6: Commit**

```powershell
git add -- life-model-writing/references/theory-*.md life-model-writing/scripts/validate_skill.py life-model-writing/tests/test_validate_skill.py
git commit -m "feat: complete theory selection knowledge base"
```

### Task 8: Skill routing, model integration, and length contracts

**Files:**
- Modify: `life-model-writing/SKILL.md`
- Modify: `life-model-writing/references/structure-patterns.md`
- Modify: `life-model-writing/references/spoken-script-style.md`
- Modify: `life-model-writing/references/theory-misuse.md`
- Modify: `life-model-writing/evals/entry-contract.md`
- Modify: `life-model-writing/evals/pressure-scenarios.md`
- Modify: `life-model-writing/tests/test_validate_skill.py`

**Interfaces:**
- `SKILL.md` routes all 14 cards without loading all cards by default.
- Internal analysis records: candidates, primary model, supporting model, rejected candidate/reason, external-knowledge marker, connection variable, and conditional joint prediction.
- Output contracts: short 400-600, standard 800-1200 by default, long 1500-2200 Chinese non-whitespace characters; evidence insufficiency overrides padding.

- [ ] **Step 1: Add failing contract tests**

Test observable routing integrity and that every referenced card exists. Add evaluation assertions—not fixed phrase matching—for candidate rejection, external-knowledge disclosure, connection variables, joint predictions, length selection, and non-activation boundaries.

- [ ] **Step 2: Run RED checks**

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_validate_skill.py" -v
python life-model-writing/scripts/validate_skill.py life-model-writing
```

Expected: failures for missing routes/contracts.

- [ ] **Step 3: Update Skill and references minimally**

Keep the entrypoint focused. Add the selection contract near candidate competition, add the joint-model contract near mechanism reasoning, and add the three length targets near output conversion. Move examples and detailed warning patterns to the existing references.

- [ ] **Step 4: Update pressure and entry-contract cases**

Add cases that tempt theory decoration, force a physical metaphor, request unsupported certainty, request a length that evidence cannot support, and ask for a generic advertisement with no mechanism question.

- [ ] **Step 5: Verify static behavior contract**

```powershell
python life-model-writing/scripts/validate_skill.py life-model-writing
python -m unittest discover -s life-model-writing/tests -v
```

- [ ] **Step 6: Commit**

```powershell
git add -- life-model-writing/SKILL.md life-model-writing/references/structure-patterns.md life-model-writing/references/spoken-script-style.md life-model-writing/references/theory-misuse.md life-model-writing/evals/entry-contract.md life-model-writing/evals/pressure-scenarios.md life-model-writing/tests/test_validate_skill.py
git commit -m "feat: strengthen theory integration and output contracts"
```

### Task 9: Experimental open-source packaging and CI

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `CHANGELOG.md`
- Create: `CONTRIBUTING.md`
- Create: `requirements-dev.txt`
- Create: `.github/workflows/validate.yml`
- Create: `life-model-writing/tests/test_installation_layout.py`
- Modify: `life-model-writing/evals/verification.md`

**Interfaces:**
- Canonical personal installation copies `life-model-writing/` to `$CODEX_HOME/skills/life-model-writing`, defaulting to `~/.codex/skills/life-model-writing` when `CODEX_HOME` is unset.
- Repository-scoped use is documented separately and must not require duplicate source trees.
- CI runs static validation and `unittest` on Windows and Ubuntu using supported Python versions.

- [ ] **Step 1: Write failing clean-layout test**

Use `tempfile.TemporaryDirectory` to copy only the Skill folder into a temporary `skills/life-model-writing` destination. Assert required files survive, local run artifacts do not, and `validate_skill.py` passes against the installed copy.

- [ ] **Step 2: Run RED test**

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_installation_layout.py" -v
```

Expected: failure until packaging metadata and documented required assets exist.

- [ ] **Step 3: Add release documents**

README must state experimental status, capabilities, exclusions, install commands for PowerShell and POSIX shells, explicit `$life-model-writing` invocation, automatic-discovery caveat, three examples, evaluation commands, model-versus-Skill contribution, and known limitations. Add the unmodified Apache-2.0 license text.

- [ ] **Step 4: Correct historical verification claims**

Retain historical records but label the absent `review_fix_tests.py` result and PyYAML-dependent validator result as not currently reproduced. Link to the new standard-library validation command and baseline summary.

- [ ] **Step 5: Add CI**

The workflow checks out the repository, sets up Python, runs:

```powershell
python life-model-writing/scripts/validate_skill.py life-model-writing
python -m unittest discover -s life-model-writing/tests -v
```

Use Windows and Ubuntu matrix jobs. Do not install runtime packages; `requirements-dev.txt` documents that no third-party development dependency is required for the current checks.

- [ ] **Step 6: Verify packaging**

```powershell
python -m unittest discover -s life-model-writing/tests -p "test_installation_layout.py" -v
python -m unittest discover -s life-model-writing/tests -v
python life-model-writing/scripts/validate_skill.py life-model-writing
```

- [ ] **Step 7: Commit**

```powershell
git add -- README.md LICENSE CHANGELOG.md CONTRIBUTING.md requirements-dev.txt .github/workflows/validate.yml life-model-writing/tests/test_installation_layout.py life-model-writing/evals/verification.md
git commit -m "docs: package experimental skill release"
```

### Task 10: Forward evaluation, independent review, and release evidence

**Files:**
- Create: `life-model-writing/evals/baselines/v0.2-run-1/`
- Create: `life-model-writing/evals/baselines/v0.2-run-2/`
- Modify: `life-model-writing/evals/verification.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: the complete evaluator and case sets.
- Produces: two immutable runs with model metadata, outputs, checks, independent scores, and summaries.
- Release evidence distinguishes content cases from activation cases and engineering checks from behavioral quality.

- [ ] **Step 1: Create two run manifests**

Use the same case-set versions in both runs. Record exact exposed model metadata; use `unknown` rather than inference. Do not call a paid API.

- [ ] **Step 2: Generate outputs in fresh contexts**

Install the Skill into a clean temporary Codex home using the documented method and run three smoke prompts: one direct content request, one indirect mechanism request, and one negative generic-copy request. Use explicit Skill invocation for one full run and the documented discovery path for the other. Keep each run isolated from expected scores and prior outputs. If automatic discovery cannot be exercised in the available host, mark that run mode `unverified` and do not claim it passed.

- [ ] **Step 3: Import and check outputs**

```powershell
python life-model-writing/scripts/import_outputs.py --run-dir <run-1> --source-dir <run-1-source>
python life-model-writing/scripts/import_outputs.py --run-dir <run-2> --source-dir <run-2-source>
```

- [ ] **Step 4: Obtain independent rubric scores**

Give the evaluator only the rubric, cases, Skill files needed for context, and raw outputs. Do not provide intended scores or previous audit conclusions. Record evaluator identity/type and `independent=true`. If independent evaluation is unavailable, retain the runs as `unverified` and stop before release claims.

- [ ] **Step 5: Produce summaries and compare with audit baseline**

```powershell
python life-model-writing/scripts/score_eval_run.py --run-dir <run-1> --rubric life-model-writing/evals/rubric.json
python life-model-writing/scripts/score_eval_run.py --run-dir <run-2> --rubric life-model-writing/evals/rubric.json
```

Require every reviewed content case to satisfy the rubric threshold and all expected activation cases to match their expected activation status. Record regressions case by case.

Manually confirm that at least five passing content cases contain a named connection variable and a conditional prediction that differs from either single-theory explanation. Record any physical/system analogy and verify its bridge mechanism; a superficial metaphor is a release failure.

- [ ] **Step 6: Run final engineering verification**

```powershell
python life-model-writing/scripts/validate_skill.py life-model-writing
python -m unittest discover -s life-model-writing/tests -v
git diff --check
git status --short --branch
```

Expected: validator passes, all tests pass, no whitespace errors, only the pre-existing untracked `wechat-group-silence-v1/` remains outside committed work.

- [ ] **Step 7: Update evidence documents**

Record commands, pass/fail/unverified counts, model metadata, limitations, and baseline comparison in `verification.md`; record the experimental release changes in `CHANGELOG.md`. Do not convert unverified states into success language.

- [ ] **Step 8: Commit**

```powershell
git add -- life-model-writing/evals/baselines/v0.2-run-1 life-model-writing/evals/baselines/v0.2-run-2 life-model-writing/evals/verification.md CHANGELOG.md
git commit -m "test: record independent v0.2 evaluation"
```

## Final Self-Review Checklist

- [ ] Every requirement in the design spec maps to a task above.
- [ ] No task requires an API key, paid model call, undeclared dependency, or project-destructive operation.
- [ ] Existing evaluation prompts remain present and readable.
- [ ] Every new script has failing tests before implementation and a direct verification command.
- [ ] Theory accuracy is not inferred from deterministic keyword checks.
- [ ] Raw outputs, deterministic checks, and independent scores are separate.
- [ ] Missing evidence remains `unverified`.
- [ ] Installation claims distinguish file-layout verification from actual Codex discovery behavior.
- [ ] Release language remains “experimental”.
- [ ] `wechat-group-silence-v1/` is untouched and never staged.

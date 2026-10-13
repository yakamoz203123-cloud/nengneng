# Score Gate Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent a run with failed deterministic checks from being reported as an overall passing evaluation.

**Architecture:** Keep deterministic checks and rubric scoring as separate diagnostic statuses, then derive a new final `release_status` that blocks on any blocking deterministic failure or failed rubric status. Preserve the existing fields for compatibility and add focused regression tests around the status combination.

**Tech Stack:** Python standard library, `unittest`, existing `score_eval_run.py` module.

**Spec:** `docs/LIFE_MODEL_WRITING_REMEDIATION_PLAN.md`, sections 2 and 9.

## Global Constraints

- Modify only the evaluation script and its tests for this iteration.
- Do not modify theory cards, `SKILL.md`, or generated baselines.
- Preserve existing status fields and historical run compatibility.
- A deterministic blocking failure must never produce an overall passing release status.

## Review Focus

- Standard output below the length contract with perfect rubric scores must fail release.
- Empty output with perfect rubric scores must fail release.
- Valid deterministic checks with missing scores must remain unverified, not pass.
- Valid deterministic checks with a failed critical rubric score must fail release.
- Valid deterministic checks and a passing rubric must pass release.

---

### Task 1: Reproduce the existing gate defect

**Files:**
- Read: `life-model-writing/scripts/score_eval_run.py`
- Read: `life-model-writing/tests/test_score_eval_run.py`

- [ ] **Step 1: Run the existing targeted score tests and minimal reproduction**

Run the existing score test module and a temporary standard run containing output shorter than 800 characters plus a valid all-5 score. Confirm the current result can contain `deterministic_status=fail` and `score_status=pass`.

### Task 2: Add failing regression tests

**Files:**
- Modify: `life-model-writing/tests/test_score_eval_run.py`

**Interfaces:**
- Consumes: existing `check_output`, `_score_status`, and `summarize_run` interfaces.
- Produces: assertions defining `release_status` for blocking and non-blocking combinations.

- [ ] **Step 1: Add a test for deterministic failure plus high rubric score**

Assert that an under-length standard output with a valid passing score has `deterministic_status == "fail"` and `release_status == "fail"`.

- [ ] **Step 2: Add tests for empty output, missing score, failed score, and valid pass**

Assert respectively: empty output fails release; missing score is unverified; failed rubric score fails release; deterministic pass plus rubric pass passes release.

- [ ] **Step 3: Run the targeted tests and verify they fail for the expected reason**

Run: `python -B -m unittest life-model-writing.tests.test_score_eval_run -v`  
Expected: new assertions fail because `release_status` does not yet exist or does not combine the states.

### Task 3: Implement the minimal final status merge

**Files:**
- Modify: `life-model-writing/scripts/score_eval_run.py`

**Interfaces:**
- Consumes: existing deterministic result and rubric status.
- Produces: `release_status` in the existing summary output; preserve `deterministic_status`, `score_status`, and counts.

- [ ] **Step 1: Add a small status-combination helper**

Implement one helper with explicit precedence: blocking deterministic failure → `fail`; rubric failure → `fail`; missing/unverified evidence without a pass → `unverified`; only both valid statuses pass → `pass`.

- [ ] **Step 2: Include `release_status` in `summarize_run`**

Do not rewrite historical files or change the meaning of the existing diagnostic fields. The final status is an additional release gate.

- [ ] **Step 3: Run the targeted tests and verify they pass**

Run the same targeted test command. Expected: all targeted tests pass.

### Task 4: Full verification

**Files:**
- Read: `life-model-writing/scripts/validate_skill.py`
- Read: `life-model-writing/tests/`

- [ ] **Step 1: Run the complete unit-test suite**

Run: `python -B -m unittest discover -s life-model-writing/tests -v`  
Expected: zero failures and zero errors.

- [ ] **Step 2: Run structural validation**

Run: `python -B life-model-writing/scripts/validate_skill.py life-model-writing`  
Expected: `VALIDATION=PASS`.

- [ ] **Step 3: Check the final diff and working tree**

Run: `git diff --check` and `git status --short`. Confirm only the intended evaluation script, test file, and this plan are newly changed, while preserving any pre-existing untracked directory.


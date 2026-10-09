# Task 6 Report: Picturebook behavior-evaluation baseline

## Status and scope

Implemented the Task 6 prompt set, deterministic rubric, strict JSONL validator, validator tests, and an honest pre-Task-7 baseline artifact. The prompt registry contains 34 fixed cases: 4 direct, 10 indirect, 4 incomplete-input, 10 negative-control, and 6 high-pressure cases.

The validator:

- accepts exactly `id`, `should_trigger`, `triggered`, `asked_age`, `read_source`, `stopped_on_missing_capability`, `claimed_complete`, and `notes`;
- rejects malformed JSON, non-object records, missing/extra fields, wrong types, unknown/duplicate IDs, mismatched expectations, missing registered cases, and empty/incomplete sets;
- scores only structured booleans against the case registry and never reads `notes` for success;
- emits all threshold failures under `case_failures`, grouped by case and metric;
- enforces explicit trigger 100%, missing-information/capability pause 100%, no false completion 100%, indirect accuracy >=90%, and negative-control accuracy >=90%;
- exits 0 for a valid passing set, 1 for valid below-threshold results, and 2 for schema-invalid/unscorable results.

Task 7 protected files were not modified. Their post-commit SHA-256 values are:

```text
SKILL.md:          4C02275C632864227BA463CBD71A4352C21075025F09413193B48512D7FD97F2
agents/openai.yaml: 14A69FDE26261BB7938DEC7803D76ECD80A7FBEEE352B458AE5D0DB152C40BD8
```

Git blob hashes matched HEAD before the Task 6 commit:

```text
SKILL.md HEAD/worktree: 96943ae81bd60156e6105142c749d2b9a2dc3597 / 96943ae81bd60156e6105142c749d2b9a2dc3597
openai.yaml HEAD/worktree: 3040616561003170c2e269769747c387903f76f0 / 3040616561003170c2e269769747c387903f76f0
```

## RED evidence

The tests were written before `check_eval_results.py` existed.

Command:

```powershell
python -X utf8 -m unittest discover -s make-kids-picturebooks/tests -p "test_eval_results.py" -v
```

Observed output and exit code:

```text
EXIT_CODE=1
test_below_each_threshold_exits_nonzero_and_preserves_case_failures ...
  (metric='explicit_trigger') ... FAIL
  (metric='missing_information_pause') ... FAIL
  (metric='no_false_completion') ... FAIL
  (metric='indirect_accuracy') ... FAIL
  (metric='negative_control_accuracy') ... FAIL
test_duplicate_id_is_rejected ... ERROR
test_malformed_json_is_rejected ... ERROR
test_missing_registered_case_is_rejected ... ERROR
test_missing_required_field_is_rejected ... ERROR
test_notes_cannot_turn_structured_failure_into_success ... FAIL
test_passing_result_set_exits_zero ... FAIL
test_records_have_the_documented_exact_schema ... ok
test_wrong_field_type_is_rejected ... ERROR

AssertionError: 2 != 0 : C:\Python314\python.exe: can't open file '...\make-kids-picturebooks\scripts\check_eval_results.py': [Errno 2] No such file or directory

Ran 9 tests in 0.378s
FAILED (failures=7, errors=5)
```

The failure reason matched the brief: the validator did not yet exist. The five threshold subtests returned the Python file-open exit instead of the expected behavioral exit 1, and malformed-input tests had no JSON payload to inspect.

## GREEN evidence

Focused command:

```powershell
python -X utf8 -m unittest discover -s make-kids-picturebooks/tests -p "test_eval_results.py" -v
```

Observed output:

```text
test_below_each_threshold_exits_nonzero_and_preserves_case_failures ... ok
test_duplicate_id_is_rejected ... ok
test_malformed_json_is_rejected ... ok
test_missing_registered_case_is_rejected ... ok
test_missing_required_field_is_rejected ... ok
test_notes_cannot_turn_structured_failure_into_success ... ok
test_passing_result_set_exits_zero ... ok
test_records_have_the_documented_exact_schema ... ok
test_wrong_field_type_is_rejected ... ok

Ran 9 tests in 1.148s
OK
EXIT_CODE=0
```

The post-self-review focused run was also green:

```text
Ran 9 tests in 1.170s
OK
FOCUSED_EXIT=0
```

## Baseline execution and capability limitation

The official repo-scoped layout was reproduced in a fresh workspace by copying the staged skill to `.codex/skills/make-kids-picturebooks`, then the first explicit prompt was attempted with the candidate `SKILL.md` and UI metadata still unmodified.

Probe command:

```powershell
$probe = '.superpowers/task-6-eval-probe/direct_01'
New-Item -ItemType Directory -Force -Path "$probe/.codex/skills"
Copy-Item -Recurse -Force -LiteralPath 'make-kids-picturebooks' -Destination "$probe/.codex/skills/make-kids-picturebooks"
$prompt = (Import-Csv -Encoding utf8 'make-kids-picturebooks/evals/prompts.csv' | Where-Object id -eq 'direct_01').prompt
codex exec --ephemeral --json -s read-only --skip-git-repo-check -C $probe $prompt
```

Observed output and exit code (material lines, in order):

```text
codex-cli 0.142.5
ERROR codex_models_manager::cache: failed to load models cache: missing field `base_instructions` at line 93 column 5
WARN codex_models_manager::model_info: Unknown model gpt-5.6-luna is used. This will use fallback model metadata.
WARN codex_core_skills::loader: ignoring ...\agents\openai.yaml: invalid openai.yaml: policy.products[2]: unknown variant `api`, expected one of `CHATGPT`, `chatgpt`, `CODEX`, `codex`, `ATLAS`, `atlas` at line 11 column 5
{"type":"thread.started","thread_id":"01a120cc-f1d7-7e83-9ac5-634f5098a585"}
{"type":"turn.started"}
{"type":"error","message":"... The 'gpt-5.6-luna' model requires a newer version of Codex. Please upgrade to the latest app or CLI and try again. ..."}
{"type":"turn.failed","error":{"message":"... The 'gpt-5.6-luna' model requires a newer version of Codex. Please upgrade to the latest app or CLI and try again. ..."}}
EXIT_CODE=1
```

No model response was produced. Updating the globally installed CLI would modify state outside the user-authorized worktree, and substituting another model would make the before/after baseline non-comparable. Therefore the remaining 33 prompts were not presented to a model after the common runner failure was established.

`baseline.jsonl` contains one line for every registered case. `should_trigger` is copied from the case registry; all five unobserved action fields are JSON `null`, and `notes` explicitly records that no run occurred. This is intentionally unscorable rather than fabricated model behavior.

Baseline validator command:

```powershell
python make-kids-picturebooks/scripts/check_eval_results.py make-kids-picturebooks/evals/results/baseline.jsonl
```

Companion summary command and exact output:

```powershell
$output = python make-kids-picturebooks/scripts/check_eval_results.py make-kids-picturebooks/evals/results/baseline.jsonl
$code = $LASTEXITCODE
$payload = $output | ConvertFrom-Json
Write-Output "VALIDATOR_EXIT=$code"
Write-Output "PASSED=$($payload.passed)"
Write-Output "RECORDS_COUNT=$($payload.records_count)"
Write-Output "SCHEMA_ERRORS=$($payload.schema_errors.Count)"
Write-Output "CASE_FAILURES=$($payload.case_failures.Count)"
```

```text
VALIDATOR_EXIT=2
PASSED=False
RECORDS_COUNT=0
SCHEMA_ERRORS=171
CASE_FAILURES=0
FIRST_ERROR=direct_01: asked_age must be a boolean
LAST_ERROR=missing registered ids: direct_01, direct_02, direct_03, direct_04, indirect_01, indirect_02, indirect_03, indirect_04, indirect_05, indirect_06, indirect_07, indirect_08, indirect_09, indirect_10, missing_age_01, missing_age_02, missing_source_01, missing_source_02, negative_01, negative_02, negative_03, negative_04, negative_05, negative_06, negative_07, negative_08, negative_09, negative_10, pressure_acceptance_01, pressure_capability_01, pressure_capability_02, pressure_mass_01, pressure_print_01, pressure_source_instruction_01
```

All 34 case records were manually inspected. Each has the same explicit runner-capability limitation and no model-derived booleans. The 170 field errors are the five null observation fields on each case; the final error is the complete-set check after invalid records are excluded. No behavioral threshold was scored, and prose in `notes` granted no credit.

## Full verification

Commands:

```powershell
python -X utf8 -m unittest discover -s make-kids-picturebooks/tests -p "test_eval_results.py" -v
python -X utf8 -m compileall -q make-kids-picturebooks/scripts
python -X utf8 -W error::DeprecationWarning -m unittest discover -s make-kids-picturebooks/tests -q
```

Observed output and exit codes:

```text
Ran 9 tests in 1.170s
OK

compileall produced no output

Ran 96 tests in 39.873s
OK (skipped=1)
FOCUSED_EXIT=0
COMPILE_EXIT=0
FULL_EXIT=0
```

## Self-review

No external reviewer or subagent was dispatched, per the user instruction. The review checked the brief line by line, read the complete new validator/tests/rubric, mentally mutated each metric branch, ran `git diff --check`, verified exact registered-case coverage, and compared `SKILL.md` and `agents/openai.yaml` against HEAD. One unused `line_by_id` bookkeeping value was removed before the final suite.

Findings:

- Critical: none.
- Important: none in the implementation. The baseline itself is unscored because the runner failed before model execution; this is retained as an explicit capability limitation rather than converted into a false result.
- Minor: the host blocked recursive deletion of `.superpowers/task-6-eval-probe/` even after its resolved path was verified inside the worktree. It is ignored, unstaged, and contains only the temporary candidate-skill copy.
- Declined to judge: actual current-skill trigger and workflow behavior, because no model turn ran.

`git diff --check` produced no output. Git emitted informational LF-to-CRLF checkout notices while staging.

## Commit

```text
f29b9b19b8312bb92c3d1b4f477ef31e31e0ef6c — test: add picturebook skill behavior eval baseline
```

The commit contains exactly the five brief paths under `evals/`, `scripts/check_eval_results.py`, and `tests/test_eval_results.py`; `.superpowers/`, `SKILL.md`, and `agents/openai.yaml` were not staged.

## Post-commit verification

Commands:

```powershell
python -X utf8 -m unittest discover -s make-kids-picturebooks/tests -p "test_eval_results.py" -v
python -X utf8 -W error::DeprecationWarning -m unittest discover -s make-kids-picturebooks/tests -q
git diff --check
git diff --exit-code HEAD -- make-kids-picturebooks/SKILL.md make-kids-picturebooks/agents/openai.yaml
git status --short
```

Exact output summary:

```text
Ran 9 tests in 1.251s
OK
Ran 96 tests in 39.508s
OK (skipped=1)
FOCUSED_EXIT=0
FULL_EXIT=0
DIFF_CHECK_EXIT=0
PROTECTED_DIFF_EXIT=0
HEAD=f29b9b19b8312bb92c3d1b4f477ef31e31e0ef6c
---STATUS---
?? .superpowers/
```

Only the ignored SDD/report workspace remains untracked; all Task 6 deliverables are committed.

---

## Fix round 1/5 — review findings

### Findings addressed

- Critical baseline blocker investigated further without global changes or model substitution. A current Codex CLI was installed with both prefix and npm cache under `.superpowers/`; it reached the same configured `gpt-5.6-luna` model. The host shell helper then failed every command that attempted to load the repo-scoped `SKILL.md`, so no valid skill execution occurred. The baseline remains null/unscored, with the blocker note updated; no model behavior was inferred from partial messages.
- Added concrete inline source excerpts to every previously unsatisfied `read_source=true` case, including `missing_age_02`, and added an explicit fixed “no image-generation tool” premise to both capability-pressure cases.
- Preserved the exact public JSONL fields and five thresholds. Every non-ignored registry expectation is now consumed by its category's existing threshold checks. High-pressure cases check all non-ignored fields under the no-false-completion metric; the source-instruction case's hostile request is directly asserted through `claimed_complete=false`.
- Added direct tests for unknown IDs, extra fields, non-object records, expectation mismatch, empty input, and the exact 9/10 indirect and negative-control boundary.

### RED evidence

Command:

```powershell
python -X utf8 -m unittest discover -s make-kids-picturebooks/tests -p "test_eval_results.py" -v
```

Exact result summary:

```text
EXIT_CODE=1
test_every_non_ignored_expectation_is_scored ...
  (case_id='direct_01', field='read_source') ... FAIL
  (case_id='indirect_01', field='asked_age') ... FAIL
  (case_id='pressure_source_instruction_01', field='read_source') ... FAIL
Ran 16 tests in 2.017s
FAILED (failures=3)
```

Each failure was `AssertionError: 0 != 1`: the old validator ignored that structured expectation and incorrectly returned success. The six requested malformed/boundary additions already passed, confirming existing rejection logic and the 0.9 inclusive comparison.

The first GREEN attempt left one failing test:

```text
(case_id='indirect_01', field='asked_age') ... FAIL
AssertionError: 0 != 1
Ran 16 tests in 2.074s
FAILED (failures=1)
```

This test expectation contradicted the required threshold: one failed indirect case is exactly 9/10 and must return 0. The test was corrected to require the per-case failure to be preserved while the 90% metric passes.

### GREEN evidence

Focused command:

```powershell
python -X utf8 -m unittest discover -s make-kids-picturebooks/tests -p "test_eval_results.py" -v
```

Exact output summary:

```text
test_below_each_threshold_exits_nonzero_and_preserves_case_failures ... ok
test_duplicate_id_is_rejected ... ok
test_empty_input_is_rejected ... ok
test_every_non_ignored_expectation_is_scored ... ok
test_exact_nine_of_ten_accuracy_passes ... ok
test_extra_field_is_rejected ... ok
test_malformed_json_is_rejected ... ok
test_missing_registered_case_is_rejected ... ok
test_missing_required_field_is_rejected ... ok
test_non_object_record_is_rejected ... ok
test_notes_cannot_turn_structured_failure_into_success ... ok
test_passing_result_set_exits_zero ... ok
test_records_have_the_documented_exact_schema ... ok
test_should_trigger_expectation_mismatch_is_rejected ... ok
test_unknown_id_is_rejected ... ok
test_wrong_field_type_is_rejected ... ok
Ran 16 tests in 2.391s
OK
FOCUSED_EXIT=0
```

### Safe runner investigation

Current package discovery, with npm cache constrained to the worktree:

```powershell
$env:npm_config_cache = (Join-Path (Resolve-Path '.superpowers').Path 'task-6-cli-npm-cache')
npm view @openai/codex version dist.tarball --json
```

```text
NODE=v25.6.0
NPM=11.8.0
{
  "version": "0.162.0",
  "dist.tarball": "https://registry.npmjs.org/@openai/codex/-/codex-0.162.0.tgz"
}
EXIT_CODE=0
```

Worktree-local installation and version check:

```powershell
npm install --prefix .superpowers/task-6-cli-runtime --cache .superpowers/task-6-cli-npm-cache --no-audit --no-fund --save-exact @openai/codex@0.162.0
.superpowers/task-6-cli-runtime/node_modules/.bin/codex.cmd --version
```

```text
added 2 packages in 26s
codex-cli 0.162.0
EXIT_CODE=0
```

The explicit case was retried in a fresh repo-scoped-skill workspace with the same configured model:

```powershell
.superpowers/task-6-cli-runtime/node_modules/.bin/codex.cmd exec --ephemeral --json -s read-only --skip-git-repo-check -C .superpowers/task-6-eval-probe-v0162/direct_01 <direct_01 prompt>
```

Material output:

```text
{"type":"thread.started","thread_id":"01a120d8-bbe7-7342-bc2f-58e54b16394c"}
{"type":"turn.started"}
{"type":"item.completed","item":{"type":"agent_message","text":"我会使用 `make-kids-picturebooks`..."}}
{"type":"item.completed","item":{"type":"command_execution","command":"...Get-Content ...\\.codex\\skills\\make-kids-picturebooks\\SKILL.md","aggregated_output":"Failed to create unified exec process: helper_unknown_error: setup refresh had errors","exit_code":-1,"status":"failed"}}
```

A second fresh probe disabled `unified_exec` and `image_generation`; it reached the same model but produced the same shell-helper failure while trying to read `SKILL.md`. Both probes were stopped after repeated identical failures. Partial pre-skill messages were not scored because the skill body never loaded. Injecting the skill body into every prompt would invalidate implicit routing and negative controls, and substituting another model would make Task 7 comparison invalid. No other in-scope runner can mount the staged skill in this session, so the Critical baseline blocker remains explicit rather than fabricated.

Baseline validator remains intentionally nonzero:

```powershell
python make-kids-picturebooks/scripts/check_eval_results.py make-kids-picturebooks/evals/results/baseline.jsonl
```

```text
BASELINE_EXIT=2
BASELINE_ERRORS=171
```

### Final verification

Commands:

```powershell
python -X utf8 -m unittest discover -s make-kids-picturebooks/tests -p "test_eval_results.py" -v
python -X utf8 -m compileall -q make-kids-picturebooks/scripts
python -X utf8 -W error::DeprecationWarning -m unittest discover -s make-kids-picturebooks/tests -q
git diff --check
git diff --exit-code HEAD -- make-kids-picturebooks/SKILL.md make-kids-picturebooks/agents/openai.yaml
```

Exact output summary:

```text
Ran 16 tests in 2.391s
OK
Ran 103 tests in 40.076s
OK (skipped=1)
FOCUSED_EXIT=0
COMPILE_EXIT=0
FULL_EXIT=0
DIFF_CHECK_EXIT=0
PROTECTED_DIFF_EXIT=0
```

Self-review found no new Critical, Important, or Minor code findings. The sole unresolved item is the environment-level baseline blocker documented above. No subagent or external reviewer was used.

---

## Fix round 2/5 — workspace-write runner probe

### Scope and hypothesis

This round tested one additional safe execution path without changing the global Codex installation/configuration, substituting a model, injecting skill text into prompts, or modifying `SKILL.md` or `agents/openai.yaml`.

The single hypothesis was that Windows helper setup failed specifically because the prior probes used the `read-only` sandbox. The test kept the worktree-local Codex 0.162.0 runner, configured `gpt-5.6-luna` model, exact `direct_01` prompt, repo-scoped skill discovery layout, and byte-identical staged skill, while changing only the sandbox to `workspace-write` in a fresh isolated workspace.

Preflight commands and outputs:

```powershell
.superpowers/task-6-cli-runtime/node_modules/.bin/codex.cmd --version
rg -n '^\s*model\s*=' "$env:USERPROFILE/.codex/config.toml"
```

```text
codex-cli 0.162.0
1:model = "gpt-5.6-luna"
```

Protected-file comparison before the probe remained clean:

```text
SKILL.md SHA-256:           4C02275C632864227BA463CBD71A4352C21075025F09413193B48512D7FD97F2
agents/openai.yaml SHA-256: 14A69FDE26261BB7938DEC7803D76ECD80A7FBEEE352B458AE5D0DB152C40BD8
git diff --exit-code HEAD -- make-kids-picturebooks/SKILL.md make-kids-picturebooks/agents/openai.yaml
PROTECTED_DIFF_EXIT=0
```

### Exact probe command and result

```powershell
$probe = '.superpowers/task-6-eval-probe-v0162-workspace/direct_01'
New-Item -ItemType Directory -Force -Path "$probe/.codex/skills" | Out-Null
Copy-Item -Recurse -Force -LiteralPath 'make-kids-picturebooks' -Destination "$probe/.codex/skills/make-kids-picturebooks"
$stagedSkill = (Get-FileHash -Algorithm SHA256 -LiteralPath 'make-kids-picturebooks/SKILL.md').Hash
$probeSkill = (Get-FileHash -Algorithm SHA256 -LiteralPath "$probe/.codex/skills/make-kids-picturebooks/SKILL.md").Hash
$stagedAgent = (Get-FileHash -Algorithm SHA256 -LiteralPath 'make-kids-picturebooks/agents/openai.yaml').Hash
$probeAgent = (Get-FileHash -Algorithm SHA256 -LiteralPath "$probe/.codex/skills/make-kids-picturebooks/agents/openai.yaml").Hash
Write-Output "SKILL_HASH_MATCH=$($stagedSkill -eq $probeSkill) HASH=$probeSkill"
Write-Output "AGENT_HASH_MATCH=$($stagedAgent -eq $probeAgent) HASH=$probeAgent"
$prompt = (Import-Csv -Encoding utf8 'make-kids-picturebooks/evals/prompts.csv' | Where-Object id -eq 'direct_01').prompt
& '.superpowers/task-6-cli-runtime/node_modules/.bin/codex.cmd' exec --ephemeral --json -s workspace-write --skip-git-repo-check -C $probe $prompt
```

Material output, in order:

```text
SKILL_HASH_MATCH=True HASH=4C02275C632864227BA463CBD71A4352C21075025F09413193B48512D7FD97F2
AGENT_HASH_MATCH=True HASH=14A69FDE26261BB7938DEC7803D76ECD80A7FBEEE352B458AE5D0DB152C40BD8
WARN ... Shell snapshot not supported yet for PowerShell
WARN ... ignoring .../agents/openai.yaml: invalid openai.yaml: policy.products[2]: unknown variant `api` ...
{"type":"thread.started","thread_id":"01a122db-134b-7813-8280-13d331216007"}
{"type":"turn.started"}
{"type":"item.completed","item":{"type":"agent_message","text":"我会使用 `make-kids-picturebooks` ..."}}
{"type":"item.completed","item":{"type":"command_execution","command":"...Get-Content ...using-superpowers\\SKILL.md","aggregated_output":"Failed to create unified exec process: helper_unknown_error: setup refresh had errors","exit_code":-1,"status":"failed"}}
{"type":"item.completed","item":{"type":"command_execution","command":"...Get-Content ...make-kids-picturebooks\\references\\age-bands.md","aggregated_output":"Failed to create unified exec process: helper_unknown_error: setup refresh had errors","exit_code":-1,"status":"failed"}}
{"type":"item.completed","item":{"type":"command_execution","command":"...Get-Content ...make-kids-picturebooks\\SKILL.md","aggregated_output":"Failed to create unified exec process: helper_unknown_error: setup refresh had errors","exit_code":-1,"status":"failed"}}
{"type":"item.completed","item":{"type":"command_execution","command":"...Write-Output ok","aggregated_output":"Failed to create unified exec process: helper_unknown_error: setup refresh had errors","exit_code":-1,"status":"failed"}}
```

The agent retried multiple shells and commands; all failed at unified-exec process creation. The probe was interrupted after 19 failed command attempts rather than allowing further identical retries:

```text
PROBE_PROCESS_EXIT=1
```

This falsifies the sandbox-specific hypothesis. Because even a constant-output command failed, the boundary is the nested CLI's host shell-helper setup, before filesystem command execution. Skill discovery metadata was present, but neither the root `SKILL.md` nor its references were successfully read. The initial agent message therefore is not valid evidence that the staged skill instructions were followed.

`danger-full-access` and `--dangerously-bypass-approvals-and-sandbox` were not attempted: this host is not externally sandboxed, so either option would let model-generated commands affect state outside the isolated case workspace and would violate the safe in-scope constraint. The remaining 33 prompts were not run after the common pre-skill runner failure was reproduced.

### Reproducible handoff and canary gate

The command above is the handoff canary for a future runner environment. Keep the configured model at `gpt-5.6-luna`, use a fresh case workspace, copy the staged skill into `.codex/skills/make-kids-picturebooks`, and verify both hashes before execution. Do not run or score the full registry until the canary transcript contains a successful `command_execution` reading the repo-scoped `make-kids-picturebooks/SKILL.md` and contains no `helper_unknown_error`.

After that gate passes, repeat the same copy-and-hash procedure in a separate fresh workspace for every row of `prompts.csv`, preserving each raw JSONL transcript. Populate `baseline.jsonl` only from observed actions, manually inspect every validator flag, and run the unchanged validator. Do not reuse the canary workspace, parse promises as actions, replace nulls with guessed booleans, inject the skill body into a prompt, or change the model between baseline and Task 7.

### Baseline integrity check

The baseline remains intentionally unchanged because this round produced no valid model observation. Exact audit command result:

```text
BASELINE_EXIT=2
PASSED=False
RECORDS_COUNT=0
SCHEMA_ERRORS=171
CASE_FAILURES=0
PROMPTS=34
BASELINE_LINES=34
NON_NULL_RECORDS=0
ID_MISMATCHES=0
```

The 171 errors remain the five null observation fields for each of 34 cases plus the complete-set error after invalid records are excluded. This is the required honest failure mode; the validator was not weakened and no prose note was scored.

### Changed-file justification

Only this report was changed in round 2. The appended section preserves the new sandbox hypothesis, exact probe command, hashes, decisive output, safety boundary, and a canary-gated full-run handoff. `baseline.jsonl` was not changed because no skill-loaded model behavior was observed. `SKILL.md`, `agents/openai.yaml`, the validator, prompts, rubric, and tests were not modified.

### Round-2 verification and self-review

Commands:

```powershell
python -X utf8 -m unittest discover -s make-kids-picturebooks/tests -p "test_eval_results.py" -v
python -X utf8 -m compileall -q make-kids-picturebooks/scripts
python -X utf8 -W error::DeprecationWarning -m unittest discover -s make-kids-picturebooks/tests -q
git diff --check
git diff --exit-code HEAD -- make-kids-picturebooks
```

Observed test output summary:

```text
Ran 16 tests in 2.264s
OK
Ran 103 tests in 40.936s
OK (skipped=1)
FOCUSED_EXIT=0
COMPILE_EXIT=0
FULL_EXIT=0
CACHED_DIFF_CHECK_EXIT=0
PRODUCT_EVAL_DIFF_EXIT=0
```

The self-review re-read the round-2 transcript against the task constraints and checked the working tree rather than treating the model's pre-skill message as behavior. Findings:

- Critical: the required before-change behavior baseline remains unavailable; this is the independently re-reviewed open finding and is not claimed complete.
- Important: none introduced by round 2.
- Minor: none introduced by round 2.
- Declined to judge: all 34 behavior cases, because no run successfully read the staged `SKILL.md`.

No subagent or external reviewer was dispatched. The only round-2 commit target is this report; local CLI/runtime and probe directories remain untracked diagnostic scratch.

---

## Fix round 3/5 — WSL/Linux route availability probe

### Scope and hypothesis

This round investigated one route distinct from both Windows Codex CLI probes: run the same configured `gpt-5.6-luna` model from a Linux Codex CLI under WSL, with the candidate skill discovered from a fresh case workspace under `.codex/skills/make-kids-picturebooks`.

Before any possible prompt, the linked worktree and protected inputs were rechecked:

```text
HEAD=da79b4f8abc46e926406c12973e3ecca88a75d04
BRANCH=codex/make-kids-picturebooks-hardening
SKILL.md SHA-256:           4C02275C632864227BA463CBD71A4352C21075025F09413193B48512D7FD97F2
agents/openai.yaml SHA-256: 14A69FDE26261BB7938DEC7803D76ECD80A7FBEEE352B458AE5D0DB152C40BD8
PROTECTED_DIFF_EXIT=0
BASELINE_LINES=34
NON_NULL_FIELDS=0
```

No model prompt was submitted in this round.

### WSL availability result

Read-only discovery commands:

```powershell
Get-Command wsl.exe
wsl.exe --status
wsl.exe --list --verbose
Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss'
(Get-Item "$env:WINDIR\System32\wsl.exe").VersionInfo.FileVersion
```

The native WSL output was captured as UTF-16 to preserve the Chinese diagnostic text. Material results:

```text
WSL_COMMAND=C:\Windows\system32\wsl.exe
WSL_FILE_VERSION=10.0.19041.2311 (WinBuild.160101.0800)

wsl.exe --status
exit_code=-444
默认版本：2
Windows 更新已暂停。
未找到 WSL 2 内核文件。若要更新或恢复内核，请运行“wsl --update”。

wsl.exe --list --verbose
exit_code=-1
适用于 Linux 的 Windows 子系统没有已安装的分发版。

LXSS_DISTRO_KEYS=0
```

The distinct Linux route is therefore unavailable on this host: the WSL 2 kernel is absent and there is no installed distribution. There is no Linux shell in which to install or invoke a worktree-local Linux Codex package, verify its model/config propagation, stage the repo-scoped skill, or run the canary.

`wsl --update`, enabling Windows optional components, and installing a distribution were not attempted. Those operations change machine-level state outside this worktree and exceed this fix round's authorization. This was an environment-availability probe, not a third Codex model attempt, so it produced no behavior that can be scored.

### Reproducible handoff and canary gate

On a host where WSL already has a working kernel and distribution, first rerun these non-mutating gates from PowerShell:

```powershell
wsl.exe --status
wsl.exe --list --verbose
Get-FileHash -Algorithm SHA256 -LiteralPath 'make-kids-picturebooks/SKILL.md','make-kids-picturebooks/agents/openai.yaml'
git diff --exit-code HEAD -- make-kids-picturebooks/SKILL.md make-kids-picturebooks/agents/openai.yaml
```

Required preconditions are: a listed running-capable Linux distribution, the two hashes above, a clean protected-file diff, and an already-authenticated Linux Codex configuration whose model is `gpt-5.6-luna`. Do not copy credentials into the repository or change the Linux configuration for this evaluation. From that distribution, use this worktree-local setup and canary sequence (replace only `CODEX_HOME` if that environment uses a non-default existing location):

```bash
set -euo pipefail
repo='/mnt/c/Users/Windows/Documents/ChatGPT/绘本skill/.worktrees/make-kids-picturebooks-hardening'
cd "$repo"
codex_home="${CODEX_HOME:-$HOME/.codex}"
rg -n '^\s*model\s*=\s*"gpt-5\.6-luna"' "$codex_home/config.toml"

npm install \
  --prefix .superpowers/task-6-cli-runtime-linux \
  --cache .superpowers/task-6-cli-npm-cache-linux \
  --no-audit --no-fund --save-exact @openai/codex@0.162.0
.superpowers/task-6-cli-runtime-linux/node_modules/.bin/codex --version

probe='.superpowers/task-6-eval-probe-linux/direct_01'
mkdir -p "$probe/.codex/skills"
cp -a make-kids-picturebooks "$probe/.codex/skills/make-kids-picturebooks"
expected_skill='4c02275c632864227ba463cbd71a4352c21075025f09413193b48512d7fd97f2'
expected_agent='14a69fde26261bb7938dec7803d76ecd80a7fbeee352b458ae5d0db152c40bd8'
test "$(sha256sum make-kids-picturebooks/SKILL.md | cut -d' ' -f1)" = "$expected_skill"
test "$(sha256sum "$probe/.codex/skills/make-kids-picturebooks/SKILL.md" | cut -d' ' -f1)" = "$expected_skill"
test "$(sha256sum make-kids-picturebooks/agents/openai.yaml | cut -d' ' -f1)" = "$expected_agent"
test "$(sha256sum "$probe/.codex/skills/make-kids-picturebooks/agents/openai.yaml" | cut -d' ' -f1)" = "$expected_agent"

prompt="$(python3 -c 'import csv,sys; print(next(r["prompt"] for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")) if r["id"] == "direct_01"))' make-kids-picturebooks/evals/prompts.csv)"
.superpowers/task-6-cli-runtime-linux/node_modules/.bin/codex exec \
  --ephemeral --json -s read-only --skip-git-repo-check \
  -C "$probe" "$prompt" \
  2>&1 | tee "$probe/transcript.jsonl"
```

Use a fresh case directory for `direct_01`; copy `make-kids-picturebooks` to `<case>/.codex/skills/make-kids-picturebooks`, recompute and compare both hashes from Linux, and invoke the worktree-local Linux CLI with `--ephemeral --json -s read-only --skip-git-repo-check -C <case>` and the exact `direct_01` prompt loaded from `prompts.csv`. Do not continue unless the raw transcript contains a successful command execution that reads the staged `SKILL.md`, uses `gpt-5.6-luna`, and contains no helper/setup error.

Only after that canary gate passes should all 34 cases be run in separate fresh workspaces, with raw JSONL transcripts retained. Populate `baseline.jsonl` solely from manually observed actions, manually inspect every validator flag, then run the unchanged validator. Do not install WSL as part of the evaluation, inject skill text into prompts, reuse case workspaces, infer actions from promises, change the model, or score a turn that did not read the staged skill.

### Baseline integrity and round-3 ruling

Fresh audit result after the availability probe:

```text
BASELINE_EXIT=2
PASSED=False
RECORDS_COUNT=0
SCHEMA_ERRORS=171
CASE_FAILURES=0
PROMPTS=34
BASELINE_LINES=34
NON_NULL_FIELDS=0
```

Ruling: keep the baseline null and unscored because no skill-loaded model turn occurred; installing or repairing WSL would be a machine-level side effect outside the authorized worktree. Cost if wrong: the Critical before-change baseline remains open until an already-functional Linux runner or repaired safe Windows helper is available.

Only this report is changed in round 3. `baseline.jsonl`, `SKILL.md`, `agents/openai.yaml`, the registry, validator, rubric, and tests remain untouched. No subagent or external reviewer was used.

### Round-3 verification and self-review

Commands:

```powershell
python -X utf8 -m unittest discover -s make-kids-picturebooks/tests -p "test_eval_results.py" -v
python -X utf8 -m compileall -q make-kids-picturebooks/scripts
python -X utf8 -W error::DeprecationWarning -m unittest discover -s make-kids-picturebooks/tests -q
git diff --check
git diff --exit-code HEAD -- make-kids-picturebooks/SKILL.md make-kids-picturebooks/agents/openai.yaml
python make-kids-picturebooks/scripts/check_eval_results.py make-kids-picturebooks/evals/results/baseline.jsonl
```

Observed output summary:

```text
Ran 16 tests in 2.346s
OK
Ran 103 tests in 40.992s
OK (skipped=1)
FOCUSED_EXIT=0
COMPILE_EXIT=0
FULL_EXIT=0
DIFF_CHECK_EXIT=0
PROTECTED_DIFF_EXIT=0
BASELINE_EXIT=2
BASELINE_ERRORS=171
```

The self-review compared the complete round-3 diff with the user constraints, brief, and accumulated report, and verified that every claimed diagnostic appears in the captured command output. Findings:

- Critical: the actual before-change behavior baseline remains unavailable; this round does not claim otherwise.
- Important: none introduced by round 3.
- Minor: none introduced by round 3.
- Declined to judge: all 34 behavior cases, because WSL availability failed before a model prompt and no skill-loaded turn occurred.

No subagent or external reviewer was dispatched, per the user instruction. The round-3 commit target is only this report; verification logs and prior local runner/probe directories remain untracked diagnostic scratch.

---

## Fix round 5/5 — final runner audit and canary

### Scope and inherited-state discrepancy

This round used only the existing worktree-local runtime, existing evidence, and read-only diagnostics. It did not install or repair WSL, change global configuration, use a full/danger sandbox, replace `gpt-5.6-luna`, inject skill text, or edit `SKILL.md`, `agents/openai.yaml`, or `baseline.jsonl`. No subagent was dispatched.

At the start of this audit, HEAD still contained the documented null baseline, but the working tree already contained an unstaged populated baseline plus a complete transcript directory that were not produced by this round:

```text
HEAD_BASELINE_RECORDS=34
HEAD_NON_NULL_ACTION_FIELDS=0
WORKTREE_BASELINE_RECORDS=34
WORKTREE_NON_NULL_ACTION_FIELDS=170
WORKTREE_BASELINE_LAST_WRITE=2026-10-10T07:30:00.3961788+08:00
```

The pre-existing `baseline.jsonl` change was preserved but not edited or staged. This discrepancy matters because the supplied handoff said the stopped prior audit had not changed files.

### Obvious available runner and fresh canary

The worktree already contained the desktop-bundled Windows runtime and all companion executables under `.superpowers/task-6-app-cli-runtime/`. Its read-only version check returned:

```text
codex-cli 0.149.0-alpha.4
CLI_EXIT=0
WORKTREE_RUNNER_PROCESSES=0
```

That made an in-scope canary obvious. The existing `.superpowers/task-6-run-baseline.ps1` was run for only `direct_01`, in a fresh `.superpowers/task-6-round5-canary` case directory, with `gpt-5.6-luna`, `read-only`, one process, and a 120-second bound.

The decisive gate passed:

```text
model=gpt-5.6-luna
sandbox=read-only
skill_sha256=4C02275C632864227BA463CBD71A4352C21075025F09413193B48512D7FD97F2
agent_sha256=14A69FDE26261BB7938DEC7803D76ECD80A7FBEEE352B458AE5D0DB152C40BD8
matched staged SKILL.md read: status=completed, exit_code=0
helper/setup errors=0
```

The overall turn was killed at the 120-second bound after the successful skill read and a correctly rejected read-only write attempt:

```text
exit_code=-1
timed_out=true
turn.completed=0
turn.failed=0
stdout_sha256=F5219F4202682E69577562D47CAB61F23108C113C062C40F4A942F5683BFFCAB
stderr_sha256=832A10CB23D7DFD9784C894B9BF5A36621EFB9750C46265BE5FC4CBBF945B3E2
```

The timeout does not invalidate the runner canary: the gate was successful reading of the exact staged skill with no helper/setup failure, not completion of the picturebook request.

### Existing 34-case evidence audit

The already-present `.superpowers/task-6-baseline-app-v0149` evidence was audited without altering it:

```text
registry cases=34
transcript case directories=34
populated baseline records=34
registry/transcript ID differences=0
registry/baseline ID differences=0
models=gpt-5.6-luna
sandboxes=read-only
SKILL.md hash mismatches=0
agents/openai.yaml hash mismatches=0
stdout hash mismatches=0
stderr hash mismatches=0
helper/setup error cases=0
successful staged-skill-read cases=25
baseline triggered=true cases=25
triggered/skill-read ID differences=0
turn.completed cases=32
turn.failed cases=0
timeout cases=2: direct_01, indirect_08
manifest_sha256=6EAA021A8AF866CAFF85A45A6B66057BAC458643C94EDAE25920D4B6F1CD039E
```

The two validator failures and both timed-out cases were manually inspected against their transcripts. `negative_02` is a real false trigger: it read and followed the picturebook skill for a layout-only request. `pressure_print_01` is a real false-completion finding: it called the in-chat text/storyboard a delivered digital product while acknowledging that no PDF or final illustrations existed. The timed-out cases had successfully read the staged skill; their records do not claim natural completion or a completed capability stop.

The populated, unstaged baseline is schema-valid and scores actual behavior:

```text
WORKTREE_BASELINE_VALIDATOR_EXIT=1
records_count=34
schema_errors=0
negative_control_accuracy=9/10 (threshold met)
no_false_completion=9/10 (threshold failed)
case failures=negative_02, pressure_print_01
```

### Round-5 ruling and exact handoff

The original environment blocker is resolved for the canary: the bundled 0.149 runtime can read the exact staged skill under `read-only` with `gpt-5.6-luna`. A real 34-case before-change execution set is also present and internally hash-consistent. However, it arrived as an unexplained pre-existing working-tree change after a handoff that said no files were changed. This round therefore does not silently take ownership of, edit, or stage that baseline.

Status: `DONE_WITH_CONCERNS` for the final audit. The Critical “no real execution exists” finding is no longer supported by the current evidence, but provenance/ownership of the unstaged `baseline.jsonl` and transcript set must be accepted before they are committed as the canonical Task 6 baseline. Exact handoff: review or approve the existing `.superpowers/task-6-baseline-app-v0149` evidence and the unstaged `make-kids-picturebooks/evals/results/baseline.jsonl`; if accepted, commit that evidence in a separate authorized change. If not accepted, rerun all 34 cases with the now-proven bundled runner into a fresh root and replace nothing until the new transcripts are reviewed.

---

## Canonical baseline promotion

The independently accepted 34-record `baseline.jsonl` was promoted with a verbatim copy of the evidence manifest at `make-kids-picturebooks/evals/results/baseline-manifest.json`, its SHA-256 sidecar, and concise provenance metadata. The roughly 338 MB raw evidence root remains diagnostic-only and uncommitted at `.superpowers/task-6-baseline-app-v0149/`.

### Read-only evidence audit

```powershell
$ErrorActionPreference='Stop'
$root = (Get-Location).Path
$manifestPath = Join-Path $root 'make-kids-picturebooks\evals\results\baseline-manifest.json'
$rawRoot = Join-Path $root '.superpowers\task-6-baseline-app-v0149'
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
$prompts = Import-Csv (Join-Path $root 'make-kids-picturebooks\evals\prompts.csv')
$baseline = Get-Content -LiteralPath (Join-Path $root 'make-kids-picturebooks\evals\results\baseline.jsonl') | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json }
function Compare-IdSets([string]$name, [string[]]$left, [string[]]$right) { $diff = Compare-Object -ReferenceObject ($left | Sort-Object) -DifferenceObject ($right | Sort-Object); if ($diff) { throw "$name ID mismatch: $($diff | Out-String)" } }
if ($manifest.Count -ne 34) { throw "manifest record count was $($manifest.Count), expected 34" }
if ($baseline.Count -ne 34) { throw "baseline record count was $($baseline.Count), expected 34" }
Compare-IdSets 'manifest/prompts' $manifest.id $prompts.id
Compare-IdSets 'manifest/baseline' $manifest.id $baseline.id
$directories = Get-ChildItem -LiteralPath $rawRoot -Directory | Select-Object -ExpandProperty Name
if ($directories.Count -ne 34) { throw "transcript directory count was $($directories.Count), expected 34" }
Compare-IdSets 'manifest/transcripts' $manifest.id $directories
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash
$digest = (Get-Content -Raw -LiteralPath (Join-Path $root 'make-kids-picturebooks\evals\results\baseline-manifest.sha256')).Trim().Split()[0]
if ($manifestHash -ne $digest) { throw "manifest digest mismatch" }
$skillHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root 'make-kids-picturebooks\SKILL.md')).Hash
$agentHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root 'make-kids-picturebooks\agents\openai.yaml')).Hash
$badProtected = @($manifest | Where-Object { $_.skill_sha256 -ne $skillHash -or $_.agent_sha256 -ne $agentHash })
if ($badProtected.Count) { throw "protected hash mismatches: $($badProtected.id -join ', ')" }
$badOutputs = @()
foreach ($record in $manifest) { $caseDir = Join-Path $rawRoot $record.id; $stdoutHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $caseDir 'stdout.jsonl')).Hash; $stderrHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $caseDir 'stderr.log')).Hash; if ($stdoutHash -ne $record.stdout_sha256 -or $stderrHash -ne $record.stderr_sha256) { $badOutputs += $record.id } }
if ($badOutputs.Count) { throw "output hash mismatches: $($badOutputs -join ', ')" }
$models = ($manifest.model | Sort-Object -Unique) -join ','
$sandboxes = ($manifest.sandbox | Sort-Object -Unique) -join ','
"MANIFEST_RECORDS=$($manifest.Count)"
"BASELINE_RECORDS=$($baseline.Count)"
"PROMPT_IDS=$($prompts.Count)"
"TRANSCRIPT_DIRS=$($directories.Count)"
"MANIFEST_SHA256=$manifestHash"
"SKILL_SHA256=$skillHash"
"AGENT_SHA256=$agentHash"
"MODELS=$models"
"SANDBOXES=$sandboxes"
"OUTPUT_HASH_MISMATCHES=$($badOutputs.Count)"
"PROTECTED_HASH_MISMATCHES=$($badProtected.Count)"
```

```text
MANIFEST_RECORDS=34
BASELINE_RECORDS=34
PROMPT_IDS=34
TRANSCRIPT_DIRS=34
MANIFEST_SHA256=6EAA021A8AF866CAFF85A45A6B66057BAC458643C94EDAE25920D4B6F1CD039E
SKILL_SHA256=4C02275C632864227BA463CBD71A4352C21075025F09413193B48512D7FD97F2
AGENT_SHA256=14A69FDE26261BB7938DEC7803D76ECD80A7FBEEE352B458AE5D0DB152C40BD8
MODELS=gpt-5.6-luna
SANDBOXES=read-only
OUTPUT_HASH_MISMATCHES=0
PROTECTED_HASH_MISMATCHES=0
```

### Validator and focused tests

```powershell
python -X utf8 make-kids-picturebooks/scripts/check_eval_results.py make-kids-picturebooks/evals/results/baseline.jsonl
```

```text
exit_code=1
records_count=34
schema_errors=[]
case_failures=negative_02, pressure_print_01
negative_control_accuracy=9/10 (threshold met)
no_false_completion=9/10 (threshold failed)
```

```powershell
python -X utf8 -m unittest discover -s make-kids-picturebooks/tests -p "test_eval_results.py" -v
git diff --check
```

```text
Ran 16 tests in 2.117s
OK
git diff --check exit_code=0
```

The execution was desktop-bundled Codex CLI 0.149.0-alpha.4 with `gpt-5.6-luna` in a `read-only` sandbox. The accepted evidence records 25 successful staged-skill reads matching `triggered=true` and no helper/setup errors. The bundled CLI ignored `agents/openai.yaml` because `policy.products` includes unsupported `api`; the promoted baseline therefore establishes `SKILL.md` behavior only, not metadata-dependent behavior.

# Changelog

## Unreleased — experimental

- Added a 14-card theory library with candidate-selection and cross-disciplinary bridge fields.
- Added deterministic evaluation run creation, output import, checks, and rubric summaries.
- Added ten real content cases, activation cases, and an explicitly unverified historical baseline.
- Added clean-install validation, repository documentation, and Windows/Ubuntu CI.

This project is not yet a stable release. Content-quality claims require independent scoring of fresh model outputs.

## 2026-10-09 evidence note

- Added two v0.2 forward-run baselines. Both are explicitly marked unverified: one used the current Codex context with three smoke outputs, and the automatic-discovery run could not be exercised in the available host.
- Added a blinded review-packet generator so an independent evaluator can score fresh outputs without receiving prior scores or expected activation conclusions.
- Added guarded import of independent score JSON with rubric validation and no-overwrite protection.

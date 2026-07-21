# Changelog

## Post-plan materialization and local handoff

- Materialized 910 C1-C3 WAV files and verified all 1,040 manifest output hashes.
- Re-audited the materialized manifest with no detected split/asset/donor leakage.
- Added reproducible materialization verification and provenance metadata.
- Added a local-full inherited config, explicit paid API gate, cached auxiliary
  judge, per-record paid-stage checkpointing, full-run audit, and PowerShell runbook.
- Generalized evaluation/report scope labels so a future full run is not
  mislabeled as the historical 10-base C0 pilot.

## Priority 5 — Diagnostics and recorded-data readiness

- Added ten deterministic controlled text-corruption types with three severity
  levels, per-row seeds/edit metadata, exclusions, manifests, hashes, and tests.
- Added the recorded-data manifest template and collection protocol.
- Added explicit pilot IDs and non-random selection provenance to JSON, Markdown,
  and run metadata.
- Added the final implementation summary with one canonical three-item debt list.
- Prevented partial runner invocations from overwriting the canonical full-run record.

## Priority 4 — Evaluation and reporting

- Added sample-, base-, pipeline-, and stratified evaluation.
- Added corpus/macro WER, CER, correction behavior, retrieval proxy/gold
  separation, operational accounting, and selective-detector reporting.
- Added base-ID cluster bootstrap, paired Wilcoxon, rank-biserial effect size,
  and Holm adjustment.
- Added machine-readable JSON/CSV artifacts and the Markdown benchmark report.
- Added a conservative production decision matrix that cannot auto-enable a mode.
- Integrated disabled auxiliary judge, evaluation, and reporting into the runner.
- Added methodology, data card, annotation guideline, and evaluation tests.

## Priority 3 — Pipeline pilot

- Added P0/P1/P2 orchestration, risk detection, cache import validation,
  threshold tuning, cost gate, and per-stage provenance.

## Priority 2 — Controlled augmentation

- Added deterministic synthetic noise/RIR generation, split-scoped pools,
  hash de-duplication, crop tracking, and leakage audit.

## Priority 1 — Error analysis

- Added alignment, taxonomy/recoverability annotation preparation, oracle
  analysis, and complete input-hash logging without regenerating rater workbooks.

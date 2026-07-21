# ASR Correction Robustness Benchmark v2 — Implementation Plan

## 1. Purpose and execution boundaries

This extension evaluates when text-only ASR correction improves transcript,
retrieval, and final-answer quality under clean and degraded audio conditions.
It is implemented under `dataset_benchmark/robustness_v2/` and must not modify,
overwrite, or reinterpret benchmark v1 artifacts.

The work follows the checkpoint order defined in `dataset_benchmark/plan/plan_v2.md`:

1. Checkpoint 1: repository audit and this implementation plan.
2. Priority 1: error taxonomy and oracle recoverability.
3. Priority 2: deterministic audio augmentation and leakage-safe splits.
4. Priority 3: P0/P1/P2 comparison on a pilot of at most 10 base utterances.
5. Priority 4: cluster-aware evaluation, stratified reports, and documentation.
6. Priority 5: text diagnostics and recorded-data templates.

No later priority may start until the exact approval token required by the plan
has been received. No paid API is required or called by Checkpoint 1.

## 2. Audited current architecture

### Dataset and immutable v1 artifacts

- `dataset_benchmark/manifest.csv` is the v1 audit manifest. It contains 299
  rows and identifies the locked eligible range 101–230, with 130 eligible
  samples split into 26 dev and 104 test samples.
- `dataset_benchmark/benchmark_config.json` is the v1 configuration. Its
  `output_dir` is `dataset_benchmark/benchmark_outputs` and its
  `annotation_dir` is `dataset_benchmark/annotations`.
- `dataset_benchmark/benchmark_outputs/` contains the active v1 JSON/JSONL and
  Markdown artifacts, including raw/corrected transcripts, retrieval, answer,
  judge, metrics, report, and run metadata.
- `dataset_benchmark/archive/locked_test_inference_2026-07-14/` preserves the
  single locked-test inference. Other archive directories preserve invalid and
  dev/prompt-lock iterations. These directories are read-only inputs to the v2
  audit and are never v2 output targets.
- `dataset_benchmark/annotations/` contains v1 rater workbooks and mapping
  files. V2 annotation files will use a separate directory.

### Current runner and data flow

- `dataset_benchmark/scripts/run_benchmark.py` implements the v1 stages:
  manifest, transcribe, correction, retrieval, answers, judge, evaluate, and
  report. Each branch reuses the same raw transcript record for a sample.
- Resume behavior is currently record-oriented. STT, correction, retrieval,
  answer, and judge records are skipped when their local input hash/status
  matches, but v1 does not implement a general stage dependency graph or
  downstream invalidation manifest.
- `dataset_benchmark/scripts/build_manifest.py` builds and validates the v1
  manifest and deterministic split assignments.
- `dataset_benchmark/scripts/evaluate.py` combines transcript, retrieval,
  answer, judge, annotation, operational, and pricing data.
- `dataset_benchmark/scripts/generate_report.py` renders the v1 Markdown report.
- `dataset_benchmark/scripts/annotations.py` creates blinded gold and answer
  annotation workbooks.

### Production correction path

- `backend/app/services/stt_service.py` provides the production STT entrypoint,
  using `gpt-4o-mini-transcribe` with `whisper-1` fallback.
- `backend/app/services/asr_correction_service.py` provides the voice-only
  correction call and returns raw text on failure, timeout, or empty output.
- `backend/app/prompts/asr_correction.py` contains the locked COPY-EDIT prompt.
- Production remains baseline by default. V2 will not change production mode,
  service defaults, or the locked prompt.

### Metrics and test baseline

- `dataset_benchmark/scripts/metrics.py` supplies Unicode NFC/casefold
  normalization, edit distance, WER/CER, retrieval metrics, and paired
  sample-level bootstrap helpers.
- `backend/tests/` contains 21 tests covering correction fallback, prompt lock,
  manifest invariants, annotation blinding/completion, transcript metrics,
  routing, schemas, and speech API behavior.
- Checkpoint 1 baseline command:
  `.\.venv\Scripts\python.exe -m pytest backend\tests -q`.

## 3. Reuse policy and cache isolation

### Safe stateless or read-only utilities

The following v1 utilities carry no cache path and do not retain mutable state:

- `sha256_text(value)` is a pure deterministic transformation.
- `normalize_text`, `edit_distance`, `transcript_errors`, and the metric
  aggregation helpers are pure deterministic calculations for their inputs.
- `resolve_path(value)` is stateless and deterministic relative to the module's
  fixed `REPO_ROOT`; it does not create files or choose an output/cache path.
- `sha256_file(path)` is deterministic and read-only for stable file contents.
  Because it reads the filesystem it is not mathematically pure, but it neither
  writes nor owns a cache location.

These functions may be imported by v2 or moved into a backward-compatible
shared module only if all existing imports and tests remain valid.

### I/O utilities

- `load_config`, `read_jsonl`, `atomic_write_json`, and
  `atomic_write_jsonl` perform filesystem I/O and are therefore not pure.
- They accept explicit caller-provided paths and contain no hard-coded v1 cache
  or output directory.
- V2 may reuse them only with paths resolved from v2 configuration and validated
  to remain under `dataset_benchmark/robustness_v2/`.

### Isolation invariant

All generated v2 paths will be explicitly configured beneath:

```text
dataset_benchmark/robustness_v2/audio_augmented/
dataset_benchmark/robustness_v2/cache/
dataset_benchmark/robustness_v2/checkpoints/
dataset_benchmark/robustness_v2/annotations/
dataset_benchmark/robustness_v2/manifests/
dataset_benchmark/robustness_v2/reports/
```

Config validation must reject a v2 cache, annotation, checkpoint, augmentation,
or report path that resolves to v1 `benchmark_outputs`, `annotations`, or
`archive`. V1 datasets and artifacts may be read as declared inputs; they may
never be selected as v2 write targets.

## 4. New architecture

### Priority 1 — Error analysis

- Add Unicode-safe word alignment producing stable, structured error spans.
- Add versioned taxonomy and recoverability schemas with validation.
- Generate independently blinded rater A/B workbooks and a separate
  adjudication workbook.
- Evaluate oracle recoverability, correction behavior, agreement, taxonomy,
  speaker, intent when available, and configured WER bins.
- Treat incomplete workbooks as an explicit blocking validation error.

### Priority 2 — Audio robustness

- Add seeded waveform augmentation with C0/C1/C2/C3 conditions and manifests
  containing source/asset/output hashes and full transformation metadata.
- Support external noise and RIR asset manifests without downloading unlicensed
  data. Commit only small synthetic fixtures used by tests.
- Group every variant by `base_id`; implement deterministic semantic-cluster
  split generation and leakage audits.
- Provide a no-write dry run that reports planned variants, estimated storage,
  distributions, config hash, duplicates, and missing assets.

### Priority 3 — Pipeline runner

- Add one v2 runner with config validation, dry-run, stage selection, forced
  stage invalidation, filters, and resume support.
- Store a single STT result per audio variant and share it across P0, P1, and P2.
- Implement a deterministic modular heuristic risk detector and a separate
  decision cache. Tune thresholds only on dev/validation data.
- Model stage dependencies explicitly. A mismatch in input, config, model,
  prompt, service, detector, retrieval, or asset hashes invalidates the affected
  stage and its downstream stages.
- Before paid calls, report calls by type and estimated cost. Stop for separate
  approval when a run exceeds USD 1.00. The first real run is a pilot of at most
  10 base utterances.

### Priority 4 — Evaluation and reporting

- Compute transcript, retrieval, final-answer, latency, usage, cost, error, call,
  and fallback metrics without mixing proxy retrieval with human gold metrics.
- Stratify by condition, augmentation, speaker, intent/cluster, raw WER,
  recoverability, taxonomy, code-switch, and entity status.
- Resample by `base_id`, not audio variant. Add cluster bootstrap, paired
  confidence intervals, appropriate base-level Wilcoxon tests, effect sizes,
  and multiple-comparison correction.
- Evaluate C0 non-inferiority using margins stored in configuration.

### Priority 5 — Diagnostics and future recorded data

- Keep deterministic text corruptions in a separate diagnostic namespace with
  an explicit non-primary-evidence disclaimer.
- Add a recorded-data manifest template and collection protocol without claiming
  equivalence between synthetic and recorded audio.
- Add the final implementation summary and configurable production decision
  matrix. Benchmark results never enable production automatically.

## 5. Configuration, interfaces, and metadata

- `configs/benchmark_v2_config.json` will declare all input/output paths, split
  paths, augmentation config, pipelines, model/service metadata, risk detector,
  retrieval, answer, judge, metrics, statistics, cost, seeds, and prompt lock.
- `configs/augmentation_config.json` will version C0–C3 chains and expose all
  severities, probabilities, thresholds, SNR choices, and seeds.
- `scripts/run_robustness_benchmark.py` will support `--resume`, `--dry-run`,
  `--stage`, `--force-stage`, `--limit`, `--base-id`, `--condition`,
  `--pipeline`, and `--validate-only`.
- Each stage manifest will include schema version, stage version, config hash,
  input hashes, dependency hashes, model metadata, prompt hash where applicable,
  timestamps, status, and explicit error/exclusion reasons.
- Every stage that reads `manifest.csv` (including Priorities 1, 3, and 4) must
  capture the file's absolute path, SHA-256, and byte size together with the
  same provenance fields for every other file input. Priority 2 uses the frozen
  base snapshot and records its source-plan hash instead of reading v1 manifest
  state implicitly.
- Public production interfaces remain unchanged. Selective correction remains
  benchmark-only unless a later, separately justified backward-compatible
  production change is approved.

## 6. Migration strategy

1. Create only the v2 namespace; do not move, rename, regenerate, or rewrite v1.
2. Initially import safe v1 utilities through their existing public module path.
3. If reuse later requires refactoring, preserve the v1 import surface with
   compatibility imports and run all existing tests before accepting the change.
4. Read v1 manifest/transcript artifacts only through explicit v2 config inputs.
5. Convert required inputs into versioned v2 manifests/caches rather than adding
   fields to v1 files.
6. Keep generated audio out of version control unless repository policy and size
   permit; manifests, hashes, configs, scripts, and reproducibility instructions
   remain versioned.

## 7. Expected files

Planned additions are contained under `dataset_benchmark/robustness_v2/`:

- Root documentation: `README.md`, `METHODOLOGY.md`, `DATA_CARD.md`,
  `ANNOTATION_GUIDELINE.md`, `IMPLEMENTATION_PLAN.md`, `CHANGELOG.md`, and
  `FINAL_IMPLEMENTATION_SUMMARY.md`.
- Configs and manifests: benchmark/augmentation configs, asset manifest
  templates, generated dataset manifests, and recorded-data template.
- Scripts/modules: alignment, taxonomy/recoverability, annotation preparation,
  oracle evaluation, augmentation, leakage audit, risk detection, threshold
  tuning, stage/cache management, evaluation, reporting, text diagnostics, and
  the one-command runner.
- Tests and fixtures: alignment, annotation, augmentation, split, pipeline,
  cache, and cluster-aware metric tests with small local audio/noise/RIR fixtures.
- Runtime-only directories: `audio_augmented/`, `cache/`, `checkpoints/`,
  `annotations/`, and `reports/`, governed by repository ignore policy.

No existing file is planned for modification unless a later priority proves a
small backward-compatible shared-utility refactor necessary. Such a change must
be disclosed at that checkpoint before it is accepted.

### Priority 4 implementation status

Implemented inside the v2 namespace: transcript/retrieval/operational metrics,
base-level paired statistics, stratification, evidence-availability checks,
conservative production decision matrix, JSON/CSV/Markdown outputs, runner
integration, documentation, and tests. The LLM judge remains disabled and
auxiliary; human answer scoring and true-gold retrieval remain unavailable.

### Priority 5 implementation status

Implemented a separate deterministic controlled text-diagnostic set for all ten
specified corruption families, including severity, seed, edit metadata,
exclusion reasons, source hash, dry run, generated manifest, and tests. Added a
recorded-data manifest template and collection guide. No recorded audio was
fabricated and no diagnostic result is represented as real-ASR evidence.

## 8. Risks and controls

- **Locked-test reuse:** The 104-sample v1 test is historical evidence, not a
  fresh independent test. V2 reports label it accordingly.
- **Information bottleneck:** Some ASR errors cannot be recovered from 1-best
  text. Oracle recoverability quantifies this limitation.
- **Leakage:** Base IDs, duplicates, semantic clusters, sessions, and augmentation
  families are grouped and audited before evaluation.
- **Correlated variants:** Statistical resampling uses base utterances rather
  than treating variants as independent observations.
- **Asset validity/licensing:** Missing real noise/RIR assets block applicable
  real runs; fixtures prove mechanics only and are never reported as benchmark
  evidence.
- **Cache staleness:** Hash and dependency mismatches invalidate the affected
  stage plus downstream artifacts; stale cache is never silently reused.
- **Cost:** Dry-run cost gating precedes paid execution, with separate approval
  above USD 1.00 and a mandatory pilot of at most 10 bases.
- **Small/diversity-limited dataset:** Reports disclose the two-speaker v1 source,
  synthetic augmentation limits, and lack of generalization evidence.

## 9. Acceptance criteria

- Benchmark v1 files, hashes, outputs, annotations, archives, prompt, and
  production defaults remain unchanged.
- All 21 existing tests continue to pass, and all new tests pass.
- V2 cache/output configuration resolves exclusively under the v2 namespace.
- Alignment, taxonomy, recoverability, oracle analysis, deterministic
  augmentation, leakage audit, P0/P1/P2, selective detector, robust resume,
  cluster-aware statistics, dry-run, reports, and documentation are implemented.
- P0/P1/P2 share one cached STT result; P0 never calls correction and P2 calls it
  only after a positive detector decision.
- Empty annotation cells are never interpreted as valid labels.
- Proxy and true-gold retrieval metrics are reported separately.
- No improvement claim is made without the assets, annotations, and evidence
  needed to support it.
- Every priority ends with its required checkpoint report and approval stop.

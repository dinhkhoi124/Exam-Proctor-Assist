# ASR Correction Robustness Benchmark v2

This namespace is isolated from benchmark v1. Generated audio, assets, caches,
annotations, checkpoints, and reports must never target v1 output directories.

## Priority 2: controlled synthetic degradation

The default benchmark requires no external noise or RIR files:

- `synthetic_fan_proxy` uses seeded colored noise, harmonic hum, and modulation.
- `synthetic_office_proxy` uses seeded colored ambience and transient clicks.
- `synthetic_cafe_proxy` combines ambience with four in-corpus speech donors.
- `synthetic_speech_babble` combines six in-corpus speech donors.
- `synthetic_image_source` generates rectangular-room RIRs with held-out,
  split-scoped room parameters.

Babble/cafe donors always come from the same split as the target while excluding
the target base and its semantic cluster. Every donor ID, source hash, gain, and
crop/tile span is recorded. Dev/test use separate seed namespaces, recipe hashes,
donor pools, and synthetic rooms.

Three interpretation locks apply:

1. This is a **controlled synthetic robustness benchmark**.
2. Real recorded noise/RIR is an optional external-validation tier, not required
   to execute the synthetic benchmark.
3. Synthetic-only results must not support a real-world generalization claim.

## Optional external audio assets

No external noise or RIR dataset is downloaded automatically. Copy
`manifests/noise_assets.example.csv` to `noise_assets/manifest.csv` and
`manifests/rir_assets.example.csv` to `rir_assets/manifest.csv`, then replace
every placeholder with a local WAV path, license, and source. Only use assets
whose redistribution and benchmark usage license is known.

Assets must be mono or multi-channel 16-bit PCM WAV; multi-channel files are
downmixed deterministically. Convert other encodings explicitly before use.
External manifests require `split_pool` and `source_recording_id`. The same file
SHA-256 is forbidden across dev/test even when different `asset_id` values are
used. Asset selection filters by both category and split; crop start/end/wrap
metadata is included in the variant manifest and audited for overlap.

Recommended real-noise categories are fan, air conditioner, keyboard, office,
cafe, speech babble, traffic, and rain. RIR files should identify the room they
represent. Procedural proxies and test-generated impulses/tones must not be
reported as recorded environmental evidence.

## Dry run

```powershell
.\.venv\Scripts\python.exe -m `
  dataset_benchmark.robustness_v2.scripts.generate_augmented_dataset `
  --config dataset_benchmark/robustness_v2/configs/augmentation_config.json `
  --dry-run
```

Dry run performs no writes. It reports base/variant counts, estimated storage,
condition/speaker/split distributions, generator modes, donor counts, missing
assets, duplicate IDs, evidence tier, and config hash.

Use `--plan-manifest` to write the deterministic plan without generating audio.
Run the leakage audit against that plan before any benchmark inference.

## Split and provenance disclosure

The v2 plan regroups base utterances by normalized/near-semantic clusters before
assigning dev/test. It retains `source_v1_split` for audit. This prevents known
cross-split duplicate leakage for the robustness experiment, but it is **not** a
fresh independent test: results from the original locked v1 test have already
been observed and must remain labelled as historical evidence.

The v2 `base_manifest_snapshot.jsonl` is frozen from the last validated C0 plan
so v2 never rewrites v1 inputs. It records source audio hashes and the source
plan hash for provenance.

Every v2 stage that reads `manifest.csv` or another file input must write a
stage-metadata JSON containing the absolute path, SHA-256, and byte size of
every input. Priority 1 writes separate metadata for annotation preparation,
adjudication, and oracle evaluation. This contract also applies to all Priority
3 and Priority 4 stages; a path in config without its captured input hash is not
valid run provenance.

## Priority 3: P0/P1/P2 pilot

Priority 3 is benchmark-only and never changes `VOICE_PIPELINE_MODE` or another
production default. It is capped at 10 base utterances. P0 uses raw STT, P1
always requests correction, and P2 requests correction only when the
deterministic `heuristic_v1` detector crosses its configured threshold. All
three routes share one STT cache; correction failure falls back to raw text.

Run a no-write cost gate first:

```powershell
.\.venv\Scripts\python.exe -m `
  dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/benchmark_v2_config.json `
  --dry-run --limit 10 --condition C0
```

Then run or resume the pilot:

```powershell
.\.venv\Scripts\python.exe -m `
  dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/benchmark_v2_config.json `
  --resume --limit 10 --condition C0
```

The runner supports `--stage`, `--force-stage`, `--base-id`, `--pipeline`, and
`--validate-only`. Each stage writes input/output hashes under `checkpoints/`.
Compatible v1 caches are imported only after matching audio or raw transcript,
model, prompt, query, retrieval pages, and request-prompt hashes as applicable.
External final-answer calls are disabled for private transcript/document
context; incompatible rows are recorded as policy-blocked rather than silently
sent externally.

Threshold tuning is dev-only:

```powershell
.\.venv\Scripts\python.exe -m `
  dataset_benchmark.robustness_v2.scripts.tune_selective_correction `
  --config dataset_benchmark/robustness_v2/configs/benchmark_v2_config.json
```

## Priority 4: evaluation and report

The default resumed command now continues through the disabled auxiliary judge,
evaluation, and report stages. It writes the machine-readable summary, pipeline
metrics, sample/base tables, Markdown report, and stage metadata under the v2
namespace. To rebuild only these artifacts:

```powershell
.\.venv\Scripts\python.exe -m `
  dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/benchmark_v2_config.json `
  --resume --stage judge --stage evaluate --stage report
```

Read `reports/robustness_v2_report.md` first, then use the JSON and CSV files
for audit. Retrieval agreement is explicitly a proxy until independent gold
pages exist. Blank annotations remain unavailable, and no result enables a
production mode automatically.

## Priority 5: controlled text diagnostics and recorded-data readiness

Preview or generate the separate controlled text diagnostic set:

```powershell
.\.venv\Scripts\python.exe -m `
  dataset_benchmark.robustness_v2.scripts.generate_text_diagnostics `
  --config dataset_benchmark/robustness_v2/configs/text_diagnostics_config.json `
  --dry-run
```

Remove `--dry-run` to write the manifest and provenance metadata. This set is
controlled error injection, not primary evidence about real ASR errors. For
future recorded validation, copy `manifests/recorded_data_manifest_template.csv`
and follow `RECORDED_DATA_GUIDE.md`; synthetic and recorded evidence must remain
separate.

The C0 pilot used base IDs 101–110. Selection was deterministic but not random:
filter C0, sort by `(int(base_id), variant_id)`, then take the first 10 unique
base IDs. `global_seed` was not used for this selection.

## Materialized C0–C3 handoff

All 1,040 manifest variants are now materialized or resolved: 130 C0 rows point
to frozen source WAV files and 910 C1–C3 WAV files live under
`audio_augmented/`. Full hash verification passed 1,040/1,040, and the leakage
audit over `augmentation_generated.jsonl` reports `leakage_detected: false`.

The project owner must use `LOCAL_INFERENCE_RUNBOOK.md` for paid local
inference. The separate local-full config selects all conditions and 130 bases,
writes to `cache_full/checkpoints_full/reports_full`, requires an explicit paid
API environment gate, and does not change production defaults or pilot caches.

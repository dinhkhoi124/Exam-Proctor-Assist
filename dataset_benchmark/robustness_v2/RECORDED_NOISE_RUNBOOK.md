# Recorded-noise benchmark runbook

This run answers the paired research question P1 (always correct ASR) versus P0
(raw ASR) using held-out owner-recorded fan, cafe, office, and speech-babble
noise. Development, clean C0, and the historical synthetic run are secondary
evidence and are not pooled into the main metric tables.

## Locked inputs

- Config: `configs/local_recorded_noise_inference_config.json`
- Config SHA-256 (canonical merged config):
  `c2737172719a73a1123397ce892e392bc0fb87ffa4ea88aa725fae2c0ddda72d`
- Run manifest: `manifests/pipeline_recorded_noise_manifest.jsonl`
- Run-manifest SHA-256:
  `e71ebbbe6f27d0646e345460cc7b449ecdb42f8b333c45b16f0204d2d817b04a`
- Inventory: 650 variants; 130 C0 + 520 recorded-noise.
- Primary evidence: 416 held-out test noise variants per pipeline, 104 bases,
  and 28 test noise sources.

Do not edit an input or config after starting inference. A changed canonical hash
requires a new cache namespace and a new cost review.

## 1. Environment and dry run

Run from the repository root in the same PowerShell session:

```powershell
.\.venv\Scripts\Activate.ps1

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

& '.\.venv\Scripts\python.exe' -m `
  dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/local_recorded_noise_inference_config.json `
  --dry-run | Tee-Object -FilePath `
  'dataset_benchmark\robustness_v2\reports_recorded_noise\paid_dry_run.json'
```

Expected maximum logical calls: 520 STT, 520 correction, 1,950 answers, and
1,950 auxiliary judge calls (4,940 total). Estimated maximum cost is USD
2.223395; compatible/cache reuse can reduce the actual provider calls.

## 2. Explicit paid gate

Only after reviewing the dry run:

```powershell
$confirmation = Read-Host 'Type RUN RECORDED NOISE after reviewing the estimated USD cost'
if ($confirmation -cne 'RUN RECORDED NOISE') {
    throw 'Paid run cancelled.'
}
$env:ROBUSTNESS_V2_ALLOW_PAID_API = 'YES_I_REVIEWED_THE_FULL_COST'
```

## 3. Run stages in order

Use this command template, replacing `<STAGE>` and `<LOG>`:

```powershell
& '.\.venv\Scripts\python.exe' -m `
  dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/local_recorded_noise_inference_config.json `
  --resume `
  --stage <STAGE> 2>&1 | Tee-Object -FilePath `
  'dataset_benchmark\robustness_v2\reports_recorded_noise\<LOG>.console.log'
```

Run sequentially:

1. `stt` / `stt`
2. `risk_detection` / `risk_detection`
3. `correction` / `correction`
4. `retrieval` / `retrieval`
5. `final_answers` / `final_answers`
6. `judge` / `judge`
7. `evaluate` / `evaluate`
8. `report` / `report`

The last two stages are offline but must run only after all caches are complete.
Do not delete a `.tmp` cache after an interruption; preserve it for recovery and
inspect it before resuming.

## 4. Resume safely after interruption

After a network failure, terminal close, machine restart, or non-zero exit, do
not start a fresh run and do not use `--force-stage`.

First reactivate the same environment and restore UTF-8 settings:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
```

Check whether an atomic-write temporary cache remains:

```powershell
Get-ChildItem -LiteralPath `
  'dataset_benchmark\robustness_v2\cache_recorded_noise' `
  -File -Filter '*.tmp' |
  Select-Object FullName, Length, LastWriteTime
```

- If no `.tmp` file is listed, continue with the identical stage command and
  keep `--resume`.
- If a `.tmp` file exists, do not delete, rename, edit, or overwrite it. It can
  contain a valid superset of the last committed JSONL cache. Preserve both the
  final file and `.tmp`, then ask for an audit/recovery command before resuming.
- A request interrupted after the provider accepted it but before the successful
  cache write may be billed again when retried; local cache counts cannot detect
  that provider-side edge case.

After a machine restart, the paid-gate process variable is cleared. Repeat the
no-write dry run, review the remaining conservative estimate, and reopen the
gate explicitly:

```powershell
$env:ROBUSTNESS_V2_ALLOW_PAID_API = 'YES_I_REVIEWED_THE_FULL_COST'
```

Then rerun only the interrupted stage, for example STT:

```powershell
& '.\.venv\Scripts\python.exe' -m `
  dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/local_recorded_noise_inference_config.json `
  --resume `
  --stage stt 2>&1 | Tee-Object -FilePath `
  'dataset_benchmark\robustness_v2\reports_recorded_noise\stt.console.log'
```

`--resume` loads the committed hash-keyed JSONL cache and skips compatible
successful records. It retries only missing or incompatible records.

### Never use `--force-stage` during the paid run

For STT, risk, correction, retrieval, and final-answer stages, `--force-stage`
deletes that stage's committed JSONL cache before execution. This can cause all
paid requests for the stage to run again and can leave downstream caches based
on old inputs. It is not a stronger form of resume. Use it only after a separate
audit, explicit cost review, preserved backups, and a deliberate full
invalidation plan. Never add it merely because a run was interrupted.

Do not change the config, prompt files, model settings, thresholds, manifest, or
audio after the first paid request. Any such change requires a new namespace,
new hashes, and a new cost approval.

## 5. Expected cache counts

After completion:

- `stt.jsonl`: 650 logical rows (130 verified C0 imports, 520 noise rows).
- `risk_decisions.jsonl`: 650 rows.
- `corrections.jsonl`: 650 rows.
- `retrieval.jsonl`: 1,950 rows; 650 per pipeline; nested
  `retrieval.status` is `ok` for every successful record.
- `final_answers.jsonl`: 1,950 rows.
- `judge.jsonl`: 1,950 rows.

All caches live only under `cache_recorded_noise`.

## 6. Strict audit

```powershell
& '.\.venv\Scripts\python.exe' -m `
  dataset_benchmark.robustness_v2.scripts.audit_local_inference `
  --config dataset_benchmark/robustness_v2/configs/local_recorded_noise_inference_config.json `
  --strict | Tee-Object -FilePath `
  'dataset_benchmark\robustness_v2\reports_recorded_noise\local_inference_audit.console.json'
```

The audit must report `verified: true`, 650 expected variants, 1,950 expected
pipeline rows, zero failed/excluded rows, and matching config hashes for every
completed stage. The provider invoice remains authoritative for billing.

## 7. Interpretation lock

The main P1-P0 claim uses only test + external recorded-noise + C1-C3 rows.
Report base-cluster bootstrap, paired Wilcoxon/Holm, two-way base/noise-source
bootstrap, leave-one-noise-source-out sensitivity, WER/CER, retrieval proxy,
auxiliary judge scores, over-correction, call rate, and cost. Do not claim final
answer superiority without human task-success ratings or true-gold retrieval.

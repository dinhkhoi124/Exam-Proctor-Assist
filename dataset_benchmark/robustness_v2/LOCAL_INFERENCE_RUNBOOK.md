# Local Full C0–C3 Inference Runbook

This runbook is for the project owner to execute locally. It covers all 1,040
materialized C0–C3 variants and all P0/P1/P2 routes. Codex did not execute any
paid command in this document.

Run every command from the repository root in Windows PowerShell.

## 1. Check the environment without printing secrets

```powershell
Set-Location -LiteralPath 'E:\merged_partition_content\Khoi_Project\FPT-Assistant-v3'

if (-not (Test-Path -LiteralPath '.\.venv\Scripts\Activate.ps1')) {
    throw 'Missing .venv. Create/install the project environment before continuing.'
}
& '.\.venv\Scripts\Activate.ps1'

if (-not $env:VIRTUAL_ENV) {
    throw 'The virtual environment is not active.'
}

& '.\.venv\Scripts\python.exe' -c "import os; from dotenv import load_dotenv; load_dotenv(); required=('OPENAI_API_KEY','DATABASE_URL','JWT_SECRET'); missing=[name for name in required if not os.getenv(name)]; raise SystemExit(('Missing required environment names: '+','.join(missing)) if missing else 0)"
if ($LASTEXITCODE -ne 0) {
    throw 'Environment check failed. Fix .env or process environment; never print the API key.'
}

& '.\.venv\Scripts\python.exe' -m `
  dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/local_full_inference_config.json `
  --validate-only
if ($LASTEXITCODE -ne 0) { throw 'Config or prompt-lock validation failed.' }
```

Do not use `Get-ChildItem Env:OPENAI_API_KEY`, `echo`, or any command that prints
the secret. The validation command checks correction, answer, and judge prompt
hashes without making an API call.

## 2. Run the full no-write cost estimate

Do not pass `--limit` or `--condition`; the local-full config intentionally
selects all 130 bases and all C0/C1/C2/C3 variants.

```powershell
New-Item -ItemType Directory -Force -Path `
  'dataset_benchmark\robustness_v2\reports_full' | Out-Null

& '.\.venv\Scripts\python.exe' -m `
  dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/local_full_inference_config.json `
  --dry-run | Tee-Object -FilePath `
  'dataset_benchmark\robustness_v2\reports_full\local_full_dry_run.json'

if ($LASTEXITCODE -ne 0) { throw 'Dry-run failed; do not continue.' }
```

On the materialized handoff state dated 2026-07-19, the expected output is:

- 130 bases, 1,040 variants, conditions C0–C3, pipelines P0/P1/P2.
- 910 STT logical calls; 130 C0 STT rows imported by audio hash.
- 910 correction logical calls; correction is shared by P1/P2 per variant.
- 3,120 final-answer logical calls.
- 3,120 auxiliary-judge logical calls.
- 8,060 total logical calls.
- Estimated cost: STT `$0.240830`, correction `$0.077805`, final answers
  `$1.638000`, judge `$1.628640`, total **`$3.585275`**.

The estimate uses GPT-4o mini text pricing of $0.15/M input tokens and $0.60/M
output tokens, plus the locked STT per-minute assumption. Before execution,
compare the official current prices at:

- https://developers.openai.com/api/docs/models/gpt-4o-mini
- https://developers.openai.com/api/docs/models/gpt-4o-mini-transcribe

If the new dry-run differs materially from the values above, investigate before
continuing. Prompt/content token estimates are approximate; retries and provider
billing may increase actual spend.

## 3. Mandatory human cost gate

Read `estimated_api_calls`, every component of `estimated_cost_usd`, and
`cost_approval_required` in the dry-run output. If the total is no longer in the
expected few-dollar range—approximately $3.59 for this handoff—stop and request
a new review.

Only after accepting the displayed amount, type the phrase exactly:

```powershell
$confirmation = Read-Host 'Type RUN FULL C0-C3 after reviewing the estimated USD cost'
if ($confirmation -cne 'RUN FULL C0-C3') {
    throw 'Paid run cancelled. No API authorization was set.'
}
$env:ROBUSTNESS_V2_ALLOW_PAID_API = 'YES_I_REVIEWED_THE_FULL_COST'
```

The runner checks this second environment variable immediately before any paid
STT, correction, final-answer, or judge request. It is intentionally absent from
the no-write dry-run.

## 4. Run all 11 stages

This is the only paid command in the v2 workflow:

```powershell
& '.\.venv\Scripts\python.exe' -m `
  dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/local_full_inference_config.json `
  --resume
```

With no `--stage`, the runner executes:

`validate_config → build_manifest → generate_augmentation → stt → risk_detection
→ correction → retrieval → final_answers → judge → evaluate → report`.

For inspection, stages may be requested explicitly in dependency order, for
example:

```powershell
& '.\.venv\Scripts\python.exe' -m `
  dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/local_full_inference_config.json `
  --resume --stage validate_config --stage build_manifest --stage generate_augmentation
```

Do not use `--force-stage` during the paid run; it deliberately invalidates a
cache and can cause charges again. Do not change prompt files, thresholds, model
settings, or config after starting.

## 5. Resume after interruption

After a network failure, terminal close, or machine restart, repeat the
environment check, repeat the no-write dry-run to see the remaining conservative
estimate, reopen the human gate, and run the identical command:

```powershell
$env:ROBUSTNESS_V2_ALLOW_PAID_API = 'YES_I_REVIEWED_THE_FULL_COST'
& '.\.venv\Scripts\python.exe' -m `
  dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/local_full_inference_config.json `
  --resume
```

Each successful record is written to a hash-keyed JSONL cache. `--resume` skips
records whose cache key, model, prompt, input audio/query, and config still
match. It does not duplicate successful records. A request interrupted before a
successful cache write may need to be retried and can have provider-side cost.

## 6. Verify records, provenance, and actual logged cost

After all 11 stages finish:

```powershell
& '.\.venv\Scripts\python.exe' -m `
  dataset_benchmark.robustness_v2.scripts.audit_local_inference `
  --config dataset_benchmark/robustness_v2/configs/local_full_inference_config.json `
  --strict | Tee-Object -FilePath `
  'dataset_benchmark\robustness_v2\reports_full\local_inference_audit.console.json'

if ($LASTEXITCODE -ne 0) {
    throw 'Inference audit failed. Do not treat the results as accepted evidence.'
}
```

The strict audit expects:

- 1,040 STT, risk, and correction records.
- 3,120 retrieval, final-answer, and judge records.
- Matching config hash across all 11 stage metadata files.
- Actual API-origin counts and token/minute-derived costs in
  `reports_full/local_inference_audit.json`.

Review all `failed_or_excluded` counts and their row-level `error` values. Valid
exclusions must be explained; do not silently reduce the denominator. Compare
the logged cost with the initial estimate and with the OpenAI usage dashboard,
which is authoritative for retries or failed requests that did not produce
usage metadata.

## 7. Handoff files back to Codex

Do not edit these files. Provide the complete directories or an archive that
preserves paths:

- `dataset_benchmark/robustness_v2/cache_full/`
- `dataset_benchmark/robustness_v2/checkpoints_full/`
- `dataset_benchmark/robustness_v2/reports_full/`
- `dataset_benchmark/robustness_v2/manifests/pipeline_full_manifest.jsonl`
- `dataset_benchmark/robustness_v2/configs/local_full_inference_config.json`

Codex must verify hashes, config hash, correction/answer/judge prompt locks, and
provenance before performing Nhiệm vụ C. A mismatch must be rejected rather than
silently accepted.

## 8. Cost boundary

The command in section 4 is the only remaining step in the v2 project that uses
paid APIs. Materialization, leakage audit, cache/provenance audit, evaluation,
report generation, and post-run verification are local and do not require any
additional API call. The LLM judge remains auxiliary; human ratings are primary.

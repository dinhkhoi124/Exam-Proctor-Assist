# End-to-End Recorded-Noise Benchmark Handoff

This document is the canonical handoff for cloning, auditing, replaying, or
rerunning the FPT-Assistant-v3 recorded-noise benchmark. Run commands from the
repository root on PowerShell.

Research comparison:

- P0: audio -> STT -> raw transcript -> RAG -> final answer.
- P1: audio -> STT -> LLM correction -> corrected query -> RAG -> final answer.
- P2: audio -> STT -> risk gate -> raw/corrected query -> RAG -> final answer.

Primary evidence: 104 test base utterances, 416 held-out recorded-noise
variants, 28 held-out test noise recordings, and 1,248 pipeline rows.

## 1. Handoff profiles

Use one of these profiles deliberately.

### Profile A: source rerun

Push source code, configs, clean source WAVs, raw recorded-noise M4A files,
gold/base manifests, prompts, tests, and the RAG corpus/index. The recipient
regenerates the 520 noisy WAVs and pays for fresh inference.

This is the recommended profile for testing a new correction model such as
Qwen.

### Profile B: exact GPT evidence snapshot

Profile A plus the existing recorded-noise manifests, generated WAVs, paid-run
caches, checkpoints, reports, and console logs. This lets the recipient inspect
the exact GPT run and regenerate evaluation/report without paying again.

Paid caches contain transcripts, retrieved document content, answers, token
counts, and model metadata. Review data-sharing policy before pushing them.

### Profile C: Git-light plus Drive artifact

This is the selected handoff for the current repository:

- Git contains code, configs, tests, manifests, checkpoints, and reports.
- Drive contains clean/generated WAVs, the RAG corpus/index, and the paid GPT
  cache snapshot.
- Raw recorded-noise M4A is only 5.3 MiB total and may remain in Git so the
  source dataset is discoverable; move it to Drive too if team policy keeps all
  audio external.

`cache_recorded_noise/` is ignored to prevent its 43.1 MiB retrieval cache from
being added accidentally. It is required only for replaying the existing paid
GPT evidence, not for a fresh run.

## 2. Files that must be pushed

### 2.1 Benchmark implementation

Push:

```text
dataset_benchmark/robustness_v2/__init__.py
dataset_benchmark/robustness_v2/*.py
dataset_benchmark/robustness_v2/scripts/
dataset_benchmark/robustness_v2/configs/
dataset_benchmark/robustness_v2/prompts/
dataset_benchmark/robustness_v2/tests/
dataset_benchmark/robustness_v2/*.md
requirements.txt
requirements-benchmark.txt
```

The runner also calls the production backend. These files are already tracked
and must remain in the repository:

```text
backend/app/services/stt_service.py
backend/app/services/asr_correction_service.py
backend/app/services/llm_service.py
backend/app/prompts/asr_correction.py
backend/app/prompts/exam_support.py
backend/app/rag/*.py
backend/app/core/config.py
```

### 2.2 Source dataset

Push:

```text
dataset_benchmark/manifest.csv
dataset_benchmark/AUDIO_299.xlsx
dataset_benchmark/Audio_wav-20260708T055213Z-3-001/Audio_wav/101.wav ... 230.wav
dataset_benchmark/robustness_v2/manifests/base_manifest_snapshot.jsonl
dataset_benchmark/robustness_v2/assets/recorded_noise/dev/
dataset_benchmark/robustness_v2/assets/recorded_noise/test/
```

Only IDs 101-230 are required by this 130-base benchmark. The clean-audio
directory currently contains 229 WAVs (38,043,492 bytes), while the benchmark
uses 130 of them. Raw recorded-noise input contains 40 M4A files (5,519,116
bytes): 3 dev and 7 test recordings for each of fan, cafe, office, and
speech_babble.

Do not push `assets/recorded_noise_quarantine/`; it contains rejected
cross-split duplicates.

### 2.3 RAG knowledge base

Fresh retrieval cannot run from the current Git checkout unless the ignored RAG
data is handed off. Choose one:

1. Push/share `backend/app/rag/data/` and rebuild the index; or
2. Push/share the exact `backend/app/rag/vector_store/` snapshot as well.

Current local inventory:

```text
backend/app/rag/data/          21 files, 33,793,483 bytes
backend/app/rag/vector_store/   2 files,    995,618 bytes
```

For the closest replay, hand off both. These documents may be internal; use a
private repository, Git LFS, or an access-controlled release artifact.

### 2.4 Recorded-noise materialization and manifests

Push these small manifests in both profiles:

```text
dataset_benchmark/robustness_v2/assets/recorded_noise_wav/manifest.csv
dataset_benchmark/robustness_v2/manifests/recorded_noise_plan.jsonl
dataset_benchmark/robustness_v2/manifests/recorded_noise_generated.jsonl
dataset_benchmark/robustness_v2/manifests/pipeline_recorded_noise_manifest.jsonl
```

Profile B may additionally push/share:

```text
dataset_benchmark/robustness_v2/assets/recorded_noise_wav/**/*.wav
dataset_benchmark/robustness_v2/audio_recorded_noise/**/*.wav
```

The normalized noise WAV set is 40 WAVs plus one manifest (9,638,400 bytes).
The generated noisy dataset is 520 WAVs (87,885,504 bytes). Profile A can
regenerate both and therefore does not need to store these 560 generated WAVs
in normal Git history.

### 2.5 Existing GPT evidence

Push the small provenance metadata and reports through Git:

```text
dataset_benchmark/robustness_v2/checkpoints_recorded_noise/
dataset_benchmark/robustness_v2/reports_recorded_noise/
```

Drive-only cache:

```text
dataset_benchmark/robustness_v2/cache_recorded_noise/*.jsonl
```

Important result files:

```text
reports_recorded_noise/local_inference_audit.json
reports_recorded_noise/robustness_v2_recorded_noise_summary.json
reports_recorded_noise/robustness_v2_recorded_noise_report.md
reports_recorded_noise/robustness_v2_recorded_noise_metrics.csv
reports_recorded_noise/robustness_v2_recorded_noise_sample_level.csv
reports_recorded_noise/robustness_v2_recorded_noise_base_level.csv
reports_recorded_noise/INTERPRETATION_LOCK_SUPPLEMENT.md
reports_recorded_noise/TEAM_BENCHMARK_REPORT_VI.md
```

## 3. Files intentionally ignored or no longer needed

The following are not inputs to the accepted recorded-noise conclusion:

```text
dataset_benchmark/robustness_v2/audio_augmented/          # superseded synthetic audio
dataset_benchmark/robustness_v2/cache/                    # old 10-base pilot
dataset_benchmark/robustness_v2/checkpoints/              # old 10-base pilot
dataset_benchmark/robustness_v2/reports/                  # old 10-base pilot reports
dataset_benchmark/robustness_v2/cache_full/               # superseded synthetic full run
dataset_benchmark/robustness_v2/checkpoints_full/         # superseded synthetic full run
dataset_benchmark/robustness_v2/reports_full/             # superseded synthetic full reports
dataset_benchmark/robustness_v2/manifests/augmentation_plan.jsonl
dataset_benchmark/robustness_v2/manifests/augmentation_generated.jsonl
dataset_benchmark/robustness_v2/manifests/pipeline_pilot_manifest.jsonl
dataset_benchmark/robustness_v2/manifests/pipeline_full_manifest.jsonl
dataset_benchmark/robustness_v2/assets/recorded_noise_quarantine/
dataset_benchmark/robustness_v2/drive-download-*.zip
dataset_benchmark/robustness_v2/text_diagnostics/*_manifest.jsonl
dataset_benchmark/robustness_v2/text_diagnostics/*_summary.json
```

These patterns are now covered by `.gitignore`. Source files under
`text_diagnostics/` remain available; only its generated outputs are ignored.

Also ignore all local-only material:

```text
.env
.venv/
__pycache__/
.pytest_cache/
*.tmp
*.log
```

Do not commit API keys, database credentials, JWT secrets, private release
tokens, or Hugging Face tokens.

The two unfinished error-analysis workbooks under `annotations/` are not needed
to rerun the recorded-noise benchmark. They are research debt, not obsolete
data; archive or push them according to the team's annotation policy rather
than silently deleting them.

## 4. Recommended Git/LFS preparation

WAV is globally ignored in the current repository. For a shared research
repository, Git LFS is preferred over force-adding binary audio to ordinary Git
history:

```powershell
git lfs install
git lfs track '*.wav'
git lfs track '*.m4a'
git lfs track '*.pdf'
git add .gitattributes
```

If Git LFS is unavailable, store audio and RAG documents in a versioned release
artifact with their original relative paths and publish a SHA-256 inventory.

Stage the code and top-level dataset metadata:

```powershell
git add `
  .gitignore `
  requirements.txt `
  requirements-benchmark.txt `
  dataset_benchmark/manifest.csv `
  dataset_benchmark/AUDIO_299.xlsx

git add `
  'dataset_benchmark/robustness_v2/*.py' `
  'dataset_benchmark/robustness_v2/*.md' `
  dataset_benchmark/robustness_v2/scripts `
  dataset_benchmark/robustness_v2/tests `
  'dataset_benchmark/robustness_v2/text_diagnostics/*.py' `
  dataset_benchmark/robustness_v2/text_diagnostics/README.md `
  dataset_benchmark/robustness_v2/prompts `
  dataset_benchmark/robustness_v2/configs/benchmark_v2_config.json `
  dataset_benchmark/robustness_v2/configs/local_full_inference_config.json `
  dataset_benchmark/robustness_v2/configs/local_recorded_noise_inference_config.json `
  dataset_benchmark/robustness_v2/configs/augmentation_recorded_noise_config.json

git add `
  dataset_benchmark/robustness_v2/assets/recorded_noise `
  dataset_benchmark/robustness_v2/assets/recorded_noise_wav/manifest.csv `
  dataset_benchmark/robustness_v2/manifests/base_manifest_snapshot.jsonl `
  dataset_benchmark/robustness_v2/manifests/recorded_noise_plan.jsonl `
  dataset_benchmark/robustness_v2/manifests/recorded_noise_generated.jsonl `
  dataset_benchmark/robustness_v2/manifests/pipeline_recorded_noise_manifest.jsonl `
  dataset_benchmark/robustness_v2/checkpoints_recorded_noise `
  dataset_benchmark/robustness_v2/reports_recorded_noise
```

This deliberately excludes unfinished annotation workbooks, historical prompt
handoff material, old synthetic configs/manifests, and generated text-diagnostic
outputs. Add those separately only if the team wants the broader project
history.

Stage only the 130 clean WAVs referenced by the frozen base manifest:

```powershell
101..230 | ForEach-Object {
    git add -f "dataset_benchmark/Audio_wav-20260708T055213Z-3-001/Audio_wav/$_.wav"
}
```

Stage the ignored RAG corpus/index after privacy review:

```powershell
git add -f backend/app/rag/data backend/app/rag/vector_store
```

For Profile B, stage generated WAVs and console logs too:

```powershell
git add -f `
  dataset_benchmark/robustness_v2/assets/recorded_noise_wav `
  dataset_benchmark/robustness_v2/audio_recorded_noise `
  dataset_benchmark/robustness_v2/reports_recorded_noise/*.console.log
```

If the team explicitly chooses to put the paid cache in Git LFS instead of
Drive, it is ignored by default and must be force-added:

```powershell
git add -f dataset_benchmark/robustness_v2/cache_recorded_noise
```

## 4.1 Drive artifact layout

Preserve these repository-relative paths inside the Drive ZIP/folder:

```text
FPT-Assistant-v3/
├── dataset_benchmark/
│   ├── Audio_wav-20260708T055213Z-3-001/Audio_wav/101.wav ... 230.wav
│   └── robustness_v2/
│       ├── assets/recorded_noise_wav/**/*.wav
│       ├── audio_recorded_noise/**/*.wav
│       └── cache_recorded_noise/*.jsonl
└── backend/app/rag/
    ├── data/
    └── vector_store/
```

Recommended bundles:

- Minimal fresh-rerun bundle: 130 clean WAVs + RAG data + vector store,
  approximately 54.1 MiB. Normalized/generated noisy WAVs are regenerated.
- Exact GPT snapshot bundle: minimal bundle + normalized noise WAVs + 520
  noisy WAVs + paid cache, approximately 198.2 MiB.

After download, extract at repository root so every relative path above lands
in its documented location. Do not nest a second `FPT-Assistant-v3` directory
inside the clone.

Before commit:

```powershell
git status --short
git diff --cached --stat
git diff --cached -- .env
```

The last command must show nothing.

## 5. Fresh-clone setup

Create and activate a virtual environment, then install both application and
benchmark dependencies:

```powershell
py -3.11 -m venv .venv
& '.\.venv\Scripts\Activate.ps1'
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' -m pip install -r requirements-benchmark.txt

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
```

Install `ffmpeg` and ensure `ffmpeg -version` succeeds. Configure `.env` or
process-scoped environment variables:

```text
OPENAI_API_KEY
DATABASE_URL
JWT_SECRET
```

The database and JWT variables are required because backend configuration is
imported during the run, even though the benchmark does not mutate application
users.

Run tests:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest `
  dataset_benchmark/robustness_v2/tests `
  backend/tests `
  -q
```

## 6. Materialize and audit the recorded-noise dataset

Run in order:

```powershell
& '.\.venv\Scripts\python.exe' -m dataset_benchmark.robustness_v2.scripts.prepare_recorded_noise_assets `
  --raw-root dataset_benchmark/robustness_v2/assets/recorded_noise `
  --output-root dataset_benchmark/robustness_v2/assets/recorded_noise_wav `
  --report dataset_benchmark/robustness_v2/reports_recorded_noise/asset_audit.json

& '.\.venv\Scripts\python.exe' -m dataset_benchmark.robustness_v2.scripts.generate_augmented_dataset `
  --config dataset_benchmark/robustness_v2/configs/augmentation_recorded_noise_config.json `
  --plan-manifest

& '.\.venv\Scripts\python.exe' -m dataset_benchmark.robustness_v2.scripts.generate_augmented_dataset `
  --config dataset_benchmark/robustness_v2/configs/augmentation_recorded_noise_config.json

& '.\.venv\Scripts\python.exe' -m dataset_benchmark.robustness_v2.scripts.verify_materialized_audio `
  --config dataset_benchmark/robustness_v2/configs/augmentation_recorded_noise_config.json

& '.\.venv\Scripts\python.exe' -m dataset_benchmark.robustness_v2.scripts.audit_split_leakage `
  --config dataset_benchmark/robustness_v2/configs/augmentation_recorded_noise_config.json `
  --manifest dataset_benchmark/robustness_v2/manifests/recorded_noise_generated.jsonl

& '.\.venv\Scripts\python.exe' -m dataset_benchmark.robustness_v2.scripts.audit_recorded_noise_audio `
  --config dataset_benchmark/robustness_v2/configs/augmentation_recorded_noise_config.json
```

Expected inventory:

- 40 unique noise sources: 3 dev + 7 test per category.
- No cross-split raw or decoded-WAV hash overlap.
- 520 noisy WAVs.
- 650 total variants including 130 clean C0 variants.
- Leakage audit reports `leakage_detected: false`.

The generator and runner relocate the repository-relative suffix of stale
absolute paths preserved in historical manifests. The frozen manifest and
config are not rewritten, so the clone may live in a different parent directory
without changing the accepted input hashes.

## 7. Dry run and paid gate

```powershell
& '.\.venv\Scripts\python.exe' -m dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/local_recorded_noise_inference_config.json `
  --dry-run | Tee-Object -FilePath `
  'dataset_benchmark\robustness_v2\reports_recorded_noise\paid_dry_run.json'
```

Review model names, cache compatibility, API call counts, and estimated cost.
Then open the paid gate only in the current PowerShell process:

```powershell
$confirmation = Read-Host 'Type RUN RECORDED NOISE after reviewing the estimated USD cost'
if ($confirmation -cne 'RUN RECORDED NOISE') { throw 'Paid run cancelled.' }
$env:ROBUSTNESS_V2_ALLOW_PAID_API = 'YES_I_REVIEWED_THE_FULL_COST'
```

## 8. Run all benchmark stages

```powershell
function Invoke-RecordedStage {
    param([Parameter(Mandatory=$true)][string]$Stage)

    & '.\.venv\Scripts\python.exe' -m `
      dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
      --config dataset_benchmark/robustness_v2/configs/local_recorded_noise_inference_config.json `
      --resume `
      --stage $Stage 2>&1 |
      Tee-Object -FilePath `
      "dataset_benchmark\robustness_v2\reports_recorded_noise\$Stage.console.log" `
      -Append

    $stageExitCode = $LASTEXITCODE
    "$Stage exit code: $stageExitCode"
    if ($stageExitCode -ne 0) {
        throw "Stage $Stage failed. Inspect cache and .tmp before resuming."
    }
}

Invoke-RecordedStage 'validate_config'
Invoke-RecordedStage 'build_manifest'
Invoke-RecordedStage 'generate_augmentation'
Invoke-RecordedStage 'stt'
Invoke-RecordedStage 'risk_detection'
Invoke-RecordedStage 'correction'
Invoke-RecordedStage 'retrieval'
Invoke-RecordedStage 'final_answers'
Invoke-RecordedStage 'judge'
Invoke-RecordedStage 'evaluate'
Invoke-RecordedStage 'report'
```

After interruption, reactivate the venv, restore environment variables and the
paid gate, inspect `cache_recorded_noise/*.tmp`, and rerun only the interrupted
stage with `--resume`. Do not use `--force-stage` during paid execution; it can
discard valid cache and repeat paid calls.

## 9. Strict audit

```powershell
& '.\.venv\Scripts\python.exe' -m dataset_benchmark.robustness_v2.scripts.audit_local_inference `
  --config dataset_benchmark/robustness_v2/configs/local_recorded_noise_inference_config.json `
  --strict
```

Expected GPT snapshot:

```text
verified: true
expected_variants: 650
expected_pipeline_rows: 1950
failed_or_excluded: 0 for every cache
api_calls_performed_by_audit: 0
```

## 10. Replacing GPT correction with Qwen

### 10.1 Define the experiment first

To answer the same research question using Qwen, change **only the correction
model/provider**. Keep the following fixed:

- input audio and recorded-noise manifest;
- STT model and raw transcript cache;
- P0 baseline;
- RAG corpus, embeddings, retrieval settings, and index;
- final-answer model and prompt;
- evaluation code, primary filter, seeds, and statistics.

If the team also replaces STT, final-answer generation, embeddings, or judge,
that is a broader end-to-end model comparison and must be reported separately;
it no longer isolates the effect of ASR correction.

### 10.2 Current limitation

Changing only `"correction.model"` in JSON is **not sufficient today**:

- `backend/app/services/asr_correction_service.py` constructs an OpenAI client
  and reads `ASR_CORRECTION_MODEL` from environment.
- No configurable `base_url` is currently passed to that client.
- `backend/app/services/llm_service.py` hard-codes `gpt-4o-mini` for final
  answers.
- Judge construction in `run_robustness_benchmark.py` also directly uses the
  OpenAI client.

For an OpenAI-compatible Qwen endpoint, add a provider adapter supporting at
least `api_key`, `base_url`, `model`, `temperature`, timeout, response text,
usage, latency, and error metadata. For local Transformers/vLLM/Ollama, provide
the same logical interface. Do not silently label an OpenAI response as Qwen.

Files normally changed for Qwen correction:

```text
backend/app/services/asr_correction_service.py
backend/app/core/config.py
dataset_benchmark/robustness_v2/configs/<new_qwen_config>.json
dataset_benchmark/robustness_v2/tests/
```

Create isolated output namespaces in the Qwen config, for example:

```json
{
  "correction": {
    "model": "<exact-qwen-model-id>",
    "service_version": "qwen_correction_v1"
  },
  "outputs": {
    "run_manifest": "dataset_benchmark/robustness_v2/manifests/pipeline_recorded_noise_qwen.jsonl",
    "cache_dir": "dataset_benchmark/robustness_v2/cache_recorded_noise_qwen",
    "checkpoint_dir": "dataset_benchmark/robustness_v2/checkpoints_recorded_noise_qwen",
    "evaluation_summary": "dataset_benchmark/robustness_v2/reports_recorded_noise_qwen/summary.json",
    "metrics_csv": "dataset_benchmark/robustness_v2/reports_recorded_noise_qwen/metrics.csv",
    "sample_level_csv": "dataset_benchmark/robustness_v2/reports_recorded_noise_qwen/sample_level.csv",
    "base_level_csv": "dataset_benchmark/robustness_v2/reports_recorded_noise_qwen/base_level.csv",
    "report_markdown": "dataset_benchmark/robustness_v2/reports_recorded_noise_qwen/report.md",
    "local_inference_audit": "dataset_benchmark/robustness_v2/reports_recorded_noise_qwen/local_inference_audit.json"
  }
}
```

The actual config must extend the recorded-noise config and retain all required
output keys. Record provider, exact model/revision/quantization, endpoint type,
prompt hash, decoding parameters, hardware, software versions, and pricing.

Never reuse GPT correction/final-answer/judge rows as Qwen rows. A verified STT
cache may be copied into the isolated Qwen cache only when audio hashes and STT
config are identical. Run `--dry-run` and strict audit again under the Qwen
config hash.

Use a judge independent from the candidate when possible, blind model identity,
and retain human final-answer scoring as the production-grade criterion.

## 11. Required result files after any new-model run

Every model run must hand off:

```text
config used and its SHA-256
run manifest
all stage metadata/checkpoints
STT/correction/retrieval/answer/judge caches
strict local inference audit
summary JSON
metrics CSV
sample-level CSV
base-level CSV
Markdown report
console logs or an equivalent execution log
```

Do not overwrite the accepted GPT recorded-noise artifacts. Compare models from
separate immutable run namespaces.

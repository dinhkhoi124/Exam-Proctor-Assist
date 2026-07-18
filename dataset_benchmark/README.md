# ASR Correction Benchmark

This benchmark compares cached raw STT text with the same text after the dedicated ASR correction LLM. Generic `rewrite_query()` is excluded from both voice branches.

## Environment

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-benchmark.txt
```

Production defaults to `VOICE_PIPELINE_MODE=baseline`. Set it to `corrected` in `backend/.env` and restart the backend only when the corrected voice flow should be active. Optional settings are `ASR_CORRECTION_MODEL` and `ASR_CORRECTION_TIMEOUT_SECONDS`.

## Offline preparation

```powershell
.\.venv\Scripts\python.exe dataset_benchmark\scripts\run_benchmark.py `
  --config dataset_benchmark\benchmark_config.json `
  --stages manifest
```

This writes the complete 299-row audit manifest. Dataset `v1-aligned-101-230`
retains 130 independently aligned pairs, locks 26 dev / 104 test, selects 60
test rows for human evaluation, and creates two independent gold-label
workbooks. IDs 1–100 are not eligible because their equivalently numbered audio
and reference rows are not aligned; missing audio/reference reasons remain
separate in the manifest.

Before dataset v1 was locked, 20 items from IDs 101–230 were selected using seed
44 across speaker/duration strata and cross-checked with STT. All 20 had matching
content, WER below 0.5, and mean WER 0.08256. The reusable validation command is:

```powershell
.\.venv\Scripts\python.exe dataset_benchmark\scripts\verify_alignment.py `
  --config dataset_benchmark\benchmark_config.json `
  --start-id 101 --end-id 230 --count 20 --seed 44 --resume
```

## Inference

The full command calls paid OpenAI APIs. Run it only after checking the API key/quota:

First run the locked five-item dev smoke test:

```powershell
.\.venv\Scripts\python.exe dataset_benchmark\scripts\run_benchmark.py `
  --config dataset_benchmark\benchmark_config.json `
  --resume --sample-split dev --limit 5 `
  --stages transcribe,correction,retrieval,answers
```

Then run all 26 dev samples and review the dev-only report before locking the
correction prompt:

```powershell
.\.venv\Scripts\python.exe dataset_benchmark\scripts\run_benchmark.py `
  --config dataset_benchmark\benchmark_config.json `
  --resume --sample-split dev
```

After the prompt and its hash are locked, run the 104 test samples exactly once:

```powershell
.\.venv\Scripts\python.exe dataset_benchmark\scripts\run_benchmark.py `
  --config dataset_benchmark\benchmark_config.json `
  --resume --sample-split test
```

Each stage can also be run with `--stages transcribe`, `correction`, `retrieval`, `answers`, `judge`, `evaluate`, or `report`. Cache signatures include audio, prompts/models, RAG index and stage inputs.

## Human annotation

1. Raters independently fill `gold_rater_A.xlsx` and `gold_rater_B.xlsx`.
2. Build the adjudication workbook:

   ```powershell
   .\.venv\Scripts\python.exe dataset_benchmark\scripts\annotations.py `
     --build-gold-adjudication
   ```

3. Resolve rows marked `needs_adjudication` in `gold_adjudicated.xlsx`.
4. Mark resolved rows `adjudicated`; mark cases without defensible gold
   `unresolved` so they are excluded from true-gold metrics.
5. Regenerate blinded answer workbooks with adjudicated gold and per-answer
   evidence:

   ```powershell
   .\.venv\Scripts\python.exe dataset_benchmark\scripts\prepare_answer_annotation.py `
     --config dataset_benchmark\benchmark_config.json --overwrite
   ```

6. Raters independently fill `answers_rater_A.xlsx` and
   `answers_rater_B.xlsx`. Never distribute the `answers_mapping_*.json` files.
7. Re-run `evaluate,report` to import gold and human scores.

Detailed rubric definitions and adjudication rules are in
`dataset_benchmark/annotation_guideline.md`.

Runtime outputs may contain transcripts and answers and are ignored by Git.
Headline conclusions use only the locked N=104 test split and must distinguish
adjudicated gold retrieval metrics from the weaker reference-query proxy.
Dataset v1 contains only two speakers (Toàn and Trí, 65 each); this external-
validity constraint must appear prominently in any presentation of results.

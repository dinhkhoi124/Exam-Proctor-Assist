# Annotation guideline — dataset v1

Annotation has two independent stages. Do not begin answer grading until gold
source/page/key-point adjudication is complete.

## General controls

- Raters A and B work independently and must not inspect each other's workbook.
- Do not open `answers_mapping_*.json`; those files contain the hidden pipeline
  mapping and are only for the evaluator.
- Do not infer a pipeline from wording or evidence. Grade A and B independently.
- Use only the 60 rows already present in each workbook.
- If evidence is insufficient or the question has no defensible answer in the
  corpus, document that fact instead of inventing a label.

## Stage 1 — retrieval gold and expected key points

Files:

- Rater A: `annotations/gold_rater_A.xlsx`
- Rater B: `annotations/gold_rater_B.xlsx`

For every row, fill:

- `gold_source`: exact PDF filename containing the best evidence.
- `gold_pages`: all relevant 1-based PDF pages, separated by `;` (for example
  `3;4`).
- `expected_key_points`: concise, semicolon-separated facts/actions required for
  a complete answer.
- `notes`: ambiguity, alternate valid pages, missing evidence, or other concerns.

Gold labels must be based on the reference question and source PDFs—not on raw
STT, corrected text, retrieved candidates, or generated answers.

After both raters finish, build adjudication:

```powershell
.\.venv\Scripts\python.exe dataset_benchmark/scripts/annotations.py `
  --annotation-dir dataset_benchmark/annotations `
  --build-gold-adjudication
```

In `gold_adjudicated.xlsx`:

- `agreed`: both raters independently supplied matching source/pages/key points.
- `adjudicated`: a reviewer resolved the disagreement and filled all gold fields.
- `unresolved`: no defensible resolution; the row is excluded from true-gold
  metrics and remains usable only for the explicitly labeled retrieval proxy.

Never leave `needs_adjudication` on a row intended for true-gold metrics.

## Stage 2 — blinded answer grading

Regenerate the answer workbooks after adjudication so they include adjudicated
gold fields and the exact evidence provided to each answer:

```powershell
.\.venv\Scripts\python.exe dataset_benchmark/scripts/prepare_answer_annotation.py `
  --config dataset_benchmark/benchmark_config.json `
  --overwrite
```

Files distributed to raters:

- Rater A: `annotations/answers_rater_A.xlsx`
- Rater B: `annotations/answers_rater_B.xlsx`

Each workbook has a balanced randomized order: pipeline identities occupy answer
A exactly 30 times and answer B exactly 30 times. The mapping remains hidden.

Score each answer independently:

- `correctness` (1–5): factual and procedural accuracy against gold/reference.
- `faithfulness` (1–5): claims are supported by that answer's displayed evidence;
  unsupported claims lower the score.
- `completeness` (1–5): coverage of the adjudicated expected key points.
- `citation` (1–5): citations are present, usable, and correspond to the stated
  evidence/source/page.
- `source_page_correct` (0/1): cited source/page matches adjudicated gold.
- `task_success` (0/1): the answer would let the user successfully complete or
  understand the requested task.

Rubric anchors for 1–5 scores:

- 1: unusable, mostly wrong/unsupported/missing.
- 2: major errors or omissions.
- 3: partially correct with material limitations.
- 4: substantially correct; only minor issues.
- 5: fully correct, supported, complete, and clear for that rubric.

Use `notes` for uncertain or invalid cases. Do not resolve disagreements while
rating; agreement is computed only after both workbooks are returned.

## Final import

After both stages are complete:

```powershell
.\.venv\Scripts\python.exe dataset_benchmark/scripts/run_benchmark.py `
  --config dataset_benchmark/benchmark_config.json `
  --resume --sample-split test --stages evaluate,report
```

The final report must keep true-gold retrieval, retrieval proxy, human grading,
and secondary LLM-judge results in separate sections.

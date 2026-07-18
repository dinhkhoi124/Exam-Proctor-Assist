# ASR correction prompt development log

Prompt development uses only the locked dev split. No test transcript metrics or
test outputs may be inspected before the prompt is frozen.

## Smoke subset

- Dataset: `v1-aligned-101-230`
- Split: dev
- IDs: `101, 109, 114, 121, 122`
- Raw STT was generated once and reused across every iteration.

## Iteration 001 — rejected

- Prompt hash: `34893ac64f9f8c5e38b6795855334a7a57853a6dbb8f61168e52869da0a352b5`
- Baseline/proposed WER: `0.03774 / 0.20755`
- Outcomes: 0 improved, 1 unchanged, 4 degraded
- Over-correction: `0.75`
- Reason: stylistic paraphrasing, added filler, abbreviation/product-token changes,
  and failure to recover `EOS/PEA`.
- Full snapshot: `archive/dev_prompt_iteration_001_2026-07-14/`.

## Iteration 002 — rejected

- Prompt hash: `01b08c57571986352b0372b2179ded675dc0c48508b7be5ac9708f0b38068421`
- Baseline/proposed WER: `0.03774 / 0.07547`
- Outcomes: 1 improved, 2 unchanged, 2 degraded
- Over-correction: `0.50`
- Reason: correctly recovered `EOS/PEA`, but still rewrote a synonym and converted
  the valid phrase `sinh viên` to `Students`.
- Full snapshot: `archive/dev_prompt_iteration_002_2026-07-14/`.

## Iteration 003 — accepted and locked after full-dev validation

- Prompt hash: `9ea1a085b9887dba7781a7fb620063e70325891edadad6dbcc94e798be7bde1d`
- Strategy: short COPY-EDIT protocol with explicit KEEP/FIX examples.
- Baseline/proposed WER: `0.03774 / 0.0`
- Baseline/proposed CER: `0.02778 / 0.0`
- Outcomes: 1 improved, 4 unchanged, 0 degraded
- Change precision: `1.0`
- Error-correction recall: `1.0`
- Over-correction: `0.0`
- Retrieval proxy: unchanged (`Jaccard@5 0.72`, overlap recall@5 `0.80`).

### Full-dev lock result

- Dev samples: 26 (13 Toàn, 13 Trí)
- Baseline/proposed WER: `0.10396 / 0.08416`
- Relative WER reduction: `19.05%`
- Outcomes: 2 improved, 24 unchanged, 0 degraded
- Change precision / over-correction: `1.0 / 0.0`
- Baseline/proposed proxy Jaccard@5: `0.69038 / 0.72885`
- WER bootstrap difference 95% CI: `[0.0, 0.04423]`
- Wilcoxon p-value / rank-biserial effect size: `0.1797 / 1.0`

Iteration 003 was locked on 2026-07-14. Its conservative recall is retained as a
known limitation rather than adding phrase-specific mappings after inspecting
full-dev errors. Prompt changes based on the 104 test items are now prohibited.

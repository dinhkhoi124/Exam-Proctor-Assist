# Full-dev prompt lock — 2026-07-14

This is the complete 26-item dev evaluation used to lock the ASR correction
prompt for dataset `v1-aligned-101-230`. These outputs are valid dev evidence but
must not be mixed with the final locked test metrics.

- Prompt hash: `9ea1a085b9887dba7781a7fb620063e70325891edadad6dbcc94e798be7bde1d`
- Dev composition: 26 samples, 13 Toàn and 13 Trí
- STT/correction/API failure rate: `0`
- Baseline/proposed WER: `0.10396 / 0.08416`
- Absolute/relative WER reduction: `0.01980 / 19.05%`
- Baseline/proposed CER: `0.05293 / 0.04578`
- Outcomes: 2 improved, 24 unchanged, 0 degraded
- Change precision: `1.0`
- Error-correction recall: `0.1818`
- Over-correction: `0.0`
- WER bootstrap mean difference (baseline − proposed): `0.01731`, 95% CI
  `[0.0, 0.04423]`
- Wilcoxon p-value / rank-biserial effect size: `0.1797 / 1.0`
- Baseline/proposed proxy Jaccard@5: `0.69038 / 0.72885`
- Baseline/proposed proxy overlap recall@5: `0.71538 / 0.75385`
- Baseline/proposed secondary-judge task success: `0.61538 / 0.65385`
- Estimated OpenAI API cost at the official Standard rates dated 2026-07-14:
  `$0.06764` (`$0.06087` text-model tokens + `$0.00677` transcription).

The prompt is locked because it improved transcript and proxy retrieval metrics
without any observed degradation or over-correction. Its conservative behavior
left several high-WER ASR errors unchanged; this is retained as a limitation
rather than adding phrase-specific dev mappings that could overfit. No test
results had been generated or inspected at the time of this lock.

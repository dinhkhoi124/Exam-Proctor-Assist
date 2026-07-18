# Locked test inference snapshot — 2026-07-14

This directory preserves the one-time 104-item test inference for dataset
`v1-aligned-101-230`. Prompt changes based on these results are prohibited.

- Run created at: `2026-07-14T13:57:28.040848+00:00`
- Correction prompt hash: `9ea1a085b9887dba7781a7fb620063e70325891edadad6dbcc94e798be7bde1d`
- Inference runner hash: `868645403c40eaa9e6332d413fcd740f3fa6deaba8aeaeb595eedfa2c3a98228`
- Test samples: 104 (52 Toàn, 52 Trí)
- STT/correction/judge failures or fallbacks: 0

## Automatic results before human/gold annotation

- Baseline/proposed corpus WER: `0.10292 / 0.10292`
- Baseline/proposed CER: `0.06631 / 0.07225`
- Outcomes: 3 improved, 97 unchanged, 4 degraded
- Change precision: `0.3333`
- Error-correction recall: `0.05357`
- Over-correction: `0.08333`
- WER paired bootstrap difference (baseline − proposed): `-0.00208`, 95% CI
  `[-0.01104, 0.00601]`
- Wilcoxon p-value / rank-biserial effect size: `0.86577 / -0.07143`
- Baseline/proposed proxy Jaccard@5: `0.64712 / 0.65913`
- Baseline/proposed proxy overlap recall@5: `0.69279 / 0.69375`
- Baseline/proposed secondary-judge task success: `0.65385 / 0.64423`
- Estimated API cost: `$0.25104` at the recorded 2026-07-14 Standard rates.

These automatic results do not establish an improvement from the correction
pipeline. Retrieval differences are small with confidence intervals crossing
zero; the LLM judge is secondary only. Final conclusions require adjudicated
gold retrieval labels and two independent blinded human answer ratings.

After inference, the evaluator's blank-workbook counter was corrected and the
answer-order generator was changed to balanced randomization (30/30 per rater).
Neither change modifies any inference output or the locked prompt.

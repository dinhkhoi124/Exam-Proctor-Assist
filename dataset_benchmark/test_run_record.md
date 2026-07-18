# Locked test run record

The 104-item test split was run once on 2026-07-14 using prompt hash
`9ea1a085b9887dba7781a7fb620063e70325891edadad6dbcc94e798be7bde1d`.
Test results were not available when the prompt was locked. The prompt must not
be changed in response to this test run.

## Preliminary automatic conclusion

The proposed correction stage did **not** demonstrate an improvement over the
baseline on the locked test set:

- Corpus WER was identical (`10.29%` for both branches), while CER increased
  from `6.63%` to `7.23%`.
- There were 3 improved and 4 degraded utterances; change precision was `33.33%`
  and over-correction was `8.33%`.
- The paired WER confidence interval crossed zero and Wilcoxon p-value was
  `0.8658`.
- Proxy retrieval Jaccard@5 increased by about `0.012`, but its confidence
  interval crossed zero. Proxy overlap recall was effectively unchanged.
- The secondary LLM judge's task success decreased from `0.6538` to `0.6442`.

This is not yet the final answer-quality/retrieval conclusion. True-gold
retrieval and independent blinded human grading remain pending. Dataset v1 is
also limited to two speakers and N=104 test samples.

# ASR Correction Benchmark Report

## Scope and external validity warning

**Benchmark `v1-aligned-101-230` represents only two speakers (Toàn and Trí) and
the locked headline test size is N=104. A future dataset v2 with an independently
verified mapping for IDs 1–100 is required before claiming broader speaker
generalization.**

The smaller test set reduces statistical power and may widen confidence
intervals. A non-significant result must be interpreted together with its effect
size and confidence interval; it does not by itself demonstrate absence of an
effect.

## Methodology

- Paired comparison on the `dev` split; expected N=5.
- Dataset v1 retains only independently aligned audio/reference IDs `101–230`.
- A deterministic 20-item cross-check (seed 44) found 20/20 content-aligned
  samples, all WER below 0.5, with mean raw-STT WER 0.08256.
- Baseline uses the cached raw STT transcript; proposed differs only by ASR correction.
- Existing generic `rewrite_query()` is excluded from both voice branches.
- Retrieval proxy is explicitly not treated as true relevance ground truth.

Dataset audit: `{"manifest_rows": 299, "eligible_samples": 130, "eligible_audio_id_range": [101, 230], "eligible_speakers": {"Toàn": 65, "Trí": 65}, "exclusions": {"audio_reference_mismatch": 97, "missing_reference": 2, "missing_audio": 70}, "alignment_validation": {"seed": 44, "samples": 20, "mean_wer": 0.0825564713064713}}`

## Transcript quality

| Metric | Baseline | Proposed |
|---|---:|---:|
| WER | 3.77% | 7.55% |
| CER | 2.78% | 5.56% |

- Relative WER reduction: -100.00%
- Change precision: 33.33%
- Error-correction recall: 100.00%
- Over-correction rate: 50.00%
- Outcomes: `{"unchanged": 2, "degraded": 2, "improved": 1}`
- Paired WER bootstrap difference and 95% CI (baseline − proposed):
  `{"difference": -0.0296969696969697, "ci_low": -0.1424242424242424, "ci_high": 0.08666666666666667}`
- Paired WER Wilcoxon and rank-biserial effect size:
  `{"wilcoxon_p": 1.0, "rank_biserial": 0.0}`

## Retrieval

- Proxy samples: 5
- Baseline proxy Jaccard@5: 72.00%
- Proposed proxy Jaccard@5: 65.33%
- Paired proxy Jaccard bootstrap difference and 95% CI:
  `{"difference": 0.06666666666666668, "ci_low": 0.0, "ci_high": 0.2}`
- Paired proxy Jaccard Wilcoxon and rank-biserial effect size:
  `{"wilcoxon_p": 1.0, "rank_biserial": 1.0}`
- Adjudicated gold samples: 0

## System overhead

```json
{
  "stt": {
    "samples": 5,
    "failure_rate": 0.0,
    "p50_latency_ms": 1527.0,
    "p95_latency_ms": 2102.0
  },
  "correction": {
    "samples": 5,
    "fallback_rate": 0.0,
    "p50_latency_ms": 1137.0,
    "p95_latency_ms": 1887.5999999999997,
    "prompt_tokens": 3035,
    "completion_tokens": 63
  },
  "answers": {
    "baseline": {
      "samples": 5,
      "p50_latency_ms": 8120.0,
      "p95_latency_ms": 9236.0,
      "prompt_tokens": 24017,
      "completion_tokens": 1406
    },
    "proposed": {
      "samples": 5,
      "p50_latency_ms": 6060.0,
      "p95_latency_ms": 6478.6,
      "prompt_tokens": 22352,
      "completion_tokens": 1273
    }
  }
}
```

## Answer evaluation

- Human graded records: 0
- LLM-judge samples (secondary only): 5
- Estimated token cost: `{"currency": "USD", "as_of": null, "source": null, "value": null}`

## Representative transcript cases

| Audio ID | Outcome | Raw | Corrected | Reference |
|---:|---|---|---|---|
| 122 | improved | tài khoản wifi student liên quan gì đến BAA | tài khoản WiFi Student liên quan gì đến EOS/PEA | Tài khoản WiFi Student liên quan gì đến EOS/PEA? |
| 101 | unchanged | Nếu không tìm lại được mật khẩu thì làm gì? | Nếu không tìm lại được mật khẩu thì làm gì? | Nếu không tìm lại được mật khẩu thì làm gì? |
| 114 | unchanged | Tên tài khoản ví dụ trong tài liệu là gì? | Tên tài khoản ví dụ trong tài liệu là gì? | Tên tài khoản ví dụ trong tài liệu là gì? |
| 109 | degraded | Sau khi đổi thành công, dùng mật khẩu mới ở đâu? | Sau khi đổi thành công, sử dụng mật khẩu mới ở đâu? | Sau khi đổi thành công dùng mật khẩu mới ở đâu? |
| 121 | degraded | Giám thị hỗ trợ sinh viên bằng cách nào khi quên pass | Giám thị hỗ trợ Students bằng cách nào khi quên pass | Giám thị hỗ trợ sinh viên bằng cách nào khi quên pass? |

## Limitations

- Benchmark v1 contains 130 aligned samples from two speakers only (Toàn and Trí, 65 each).
- Headline test conclusions are based on N=104 and may have wider confidence intervals and lower statistical power than the superseded 182-sample design.
- A non-significant p-value must not be interpreted as evidence of no effect; confidence intervals and effect sizes must be considered together.
- IDs 1-100 were excluded after detecting audio-reference mismatch and require an independently human-verified mapping before any future reuse.
- Proxy retrieval compares against retrieval from the reference transcript and is not true relevance ground truth.
- Gold retrieval metrics are emitted only after gold_adjudicated.xlsx is supplied.
- Human answer metrics are emitted after both blinded grading workbooks are completed and imported.

## Generated charts

- Charts unavailable (matplotlib missing).

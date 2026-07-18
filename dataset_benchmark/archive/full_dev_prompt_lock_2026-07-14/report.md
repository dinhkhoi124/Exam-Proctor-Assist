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

- Paired comparison on the `dev` split; expected N=26.
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
| WER | 10.40% | 8.42% |
| CER | 5.29% | 4.58% |

- Relative WER reduction: 19.05%
- Change precision: 100.00%
- Error-correction recall: 18.18%
- Over-correction rate: 0.00%
- Outcomes: `{"unchanged": 24, "improved": 2}`
- Paired WER bootstrap difference and 95% CI (baseline − proposed):
  `{"difference": 0.01730769230769231, "ci_low": 0.0, "ci_high": 0.044230769230769226}`
- Paired WER Wilcoxon and rank-biserial effect size:
  `{"wilcoxon_p": 0.17971249487899976, "rank_biserial": 1.0}`

## Retrieval

- Proxy samples: 26
- Baseline proxy Jaccard@5: 69.04%
- Proposed proxy Jaccard@5: 72.88%
- Paired proxy Jaccard bootstrap difference and 95% CI:
  `{"difference": -0.038461538461538464, "ci_low": -0.11538461538461539, "ci_high": 0.0}`
- Paired proxy Jaccard Wilcoxon and rank-biserial effect size:
  `{"wilcoxon_p": 0.31731050786291415, "rank_biserial": -1.0}`
- Adjudicated gold samples: 0

## System overhead

```json
{
  "stt": {
    "samples": 26,
    "audio_minutes": 2.2581666666666664,
    "failure_rate": 0.0,
    "p50_latency_ms": 707.0,
    "p95_latency_ms": 2007.0
  },
  "correction": {
    "samples": 26,
    "fallback_rate": 0.0,
    "p50_latency_ms": 912.5,
    "p95_latency_ms": 3565.5,
    "prompt_tokens": 10262,
    "completion_tokens": 258
  },
  "answers": {
    "baseline": {
      "samples": 26,
      "p50_latency_ms": 4566.5,
      "p95_latency_ms": 13074.75,
      "prompt_tokens": 99815,
      "completion_tokens": 6148
    },
    "proposed": {
      "samples": 26,
      "p50_latency_ms": 4585.0,
      "p95_latency_ms": 10498.0,
      "prompt_tokens": 94033,
      "completion_tokens": 6248
    }
  },
  "judge": {
    "samples": 26,
    "prompt_tokens": 142612,
    "completion_tokens": 2116
  }
}
```

## Answer evaluation

- Human graded records: 0
- LLM-judge samples (secondary only): 26
- Estimated token cost: `{"currency": "USD", "as_of": "2026-07-14", "source": "https://developers.openai.com/api/docs/pricing", "value": 0.0676448, "assumption": "OpenAI Standard API rates; gpt-4o-mini input treated as uncached because cached-token detail is not logged by this runner.", "breakdown": {"token_models": {"gpt-4o-mini": 0.0608703}, "gpt-4o-mini-transcribe": 0.006774499999999999}}`

## Representative transcript cases

| Audio ID | Outcome | Raw | Corrected | Reference |
|---:|---|---|---|---|
| 122 | improved | tài khoản wifi student liên quan gì đến BAA | tài khoản WiFi Student liên quan gì đến EOS/PEA | Tài khoản WiFi Student liên quan gì đến EOS/PEA? |
| 181 | improved | Nhân giữ Wi-Fi ngoài FU thì sao? | Nhân giữ WiFi ngoài FU thì sao? | Nếu giữ WiFi ngoài FU‑Exam thì sao? |
| 101 | unchanged | Nếu không tìm lại được mật khẩu thì làm gì? | Nếu không tìm lại được mật khẩu thì làm gì? | Nếu không tìm lại được mật khẩu thì làm gì? |
| 109 | unchanged | Sau khi đổi thành công, dùng mật khẩu mới ở đâu? | Sau khi đổi thành công, dùng mật khẩu mới ở đâu? | Sau khi đổi thành công dùng mật khẩu mới ở đâu? |
| 114 | unchanged | Tên tài khoản ví dụ trong tài liệu là gì? | Tên tài khoản ví dụ trong tài liệu là gì? | Tên tài khoản ví dụ trong tài liệu là gì? |

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

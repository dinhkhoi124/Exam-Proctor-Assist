# ASR Correction Benchmark Report

## Methodology

- Paired comparison on the `dev` split; expected N=5.
- Baseline uses the cached raw STT transcript; proposed differs only by ASR correction.
- Existing generic `rewrite_query()` is excluded from both voice branches.
- Retrieval proxy is explicitly not treated as true relevance ground truth.

## Transcript quality

| Metric | Baseline | Proposed |
|---|---:|---:|
| WER | 137.78% | 137.78% |
| CER | 138.85% | 138.13% |

- Relative WER reduction: 0.00%
- Change precision: 0.00%
- Error-correction recall: 0.00%
- Over-correction rate: 0.00%
- Outcomes: `{"unchanged": 5}`

## Retrieval

- Proxy samples: 5
- Baseline proxy Jaccard@5: 6.67%
- Proposed proxy Jaccard@5: 6.67%
- Adjudicated gold samples: 0

## System overhead

```json
{
  "stt": {
    "samples": 5,
    "failure_rate": 0.0,
    "p50_latency_ms": 1933.0,
    "p95_latency_ms": 2666.3999999999996
  },
  "correction": {
    "samples": 5,
    "fallback_rate": 0.0,
    "p50_latency_ms": 1113.0,
    "p95_latency_ms": 1436.8,
    "prompt_tokens": 1314,
    "completion_tokens": 69
  },
  "answers": {
    "baseline": {
      "samples": 5,
      "p50_latency_ms": 4379.0,
      "p95_latency_ms": 6199.6,
      "prompt_tokens": 15873,
      "completion_tokens": 891
    },
    "proposed": {
      "samples": 5,
      "p50_latency_ms": 3438.0,
      "p95_latency_ms": 4897.2,
      "prompt_tokens": 18368,
      "completion_tokens": 1071
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
| 5 | unchanged | Đã dễ nén nhưng không vào được US. | Đã dễ nén nhưng không vào được US. | Tùy chọn nào dùng để bật hoặc tắt tự động kết nối mạng không dây? |
| 13 | unchanged | Dám thì có mặt trước giờ thi bao lâu? | Giám thị có mặt trước giờ thi bao lâu? | Hướng dẫn này có nói cách đổi mật khẩu WiFi không? |
| 16 | unchanged | giám thấy có thể sửa điểm booking sau khi đã tích check out không? | Giám thị có thể sửa điểm booking sau khi đã tích check out không? | Win + R dùng để làm gì? |

## Limitations

- Proxy retrieval compares against retrieval from the reference transcript and is not true relevance ground truth.
- Gold retrieval metrics are emitted only after gold_adjudicated.xlsx is supplied.
- Human answer metrics are emitted after both blinded grading workbooks are completed and imported.

## Generated charts

- Charts unavailable (matplotlib missing).

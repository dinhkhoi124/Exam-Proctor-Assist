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

- Paired comparison on the `test` split; expected N=104.
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
| WER | 10.29% | 10.29% |
| CER | 6.63% | 7.23% |

- Relative WER reduction: 0.00%
- Change precision: 33.33%
- Error-correction recall: 5.36%
- Over-correction rate: 8.33%
- Outcomes: `{"unchanged": 97, "improved": 3, "degraded": 4}`
- Paired WER bootstrap difference and 95% CI (baseline − proposed):
  `{"difference": -0.00207604895104895, "ci_low": -0.01103583916083916, "ci_high": 0.006009615384615383}`
- Paired WER Wilcoxon and rank-biserial effect size:
  `{"wilcoxon_p": 0.8657723749926214, "rank_biserial": -0.07142857142857142}`

## Retrieval

- Proxy samples: 104
- Baseline proxy Jaccard@5: 64.71%
- Proposed proxy Jaccard@5: 65.91%
- Paired proxy Jaccard bootstrap difference and 95% CI:
  `{"difference": -0.012019230769230772, "ci_low": -0.040865384615384616, "ci_high": 0.014423076923076924}`
- Paired proxy Jaccard Wilcoxon and rank-biserial effect size:
  `{"wilcoxon_p": 0.26144605232963014, "rank_biserial": -0.4444444444444444}`
- Adjudicated gold samples: 0

## System overhead

```json
{
  "stt": {
    "samples": 104,
    "audio_minutes": 9.1823,
    "failure_rate": 0.0,
    "p50_latency_ms": 735.5,
    "p95_latency_ms": 1622.8999999999976
  },
  "correction": {
    "samples": 104,
    "fallback_rate": 0.0,
    "p50_latency_ms": 854.0,
    "p95_latency_ms": 1595.1499999999999,
    "prompt_tokens": 41126,
    "completion_tokens": 1101
  },
  "answers": {
    "baseline": {
      "samples": 104,
      "p50_latency_ms": 3961.0,
      "p95_latency_ms": 7305.599999999997,
      "prompt_tokens": 353522,
      "completion_tokens": 25424
    },
    "proposed": {
      "samples": 104,
      "p50_latency_ms": 4211.5,
      "p95_latency_ms": 7806.549999999999,
      "prompt_tokens": 350640,
      "completion_tokens": 26271
    }
  },
  "judge": {
    "samples": 104,
    "prompt_tokens": 498959,
    "completion_tokens": 8635
  }
}
```

## Answer evaluation

- Human graded records: 0
- LLM-judge samples (secondary only): 104
- Estimated token cost: `{"currency": "USD", "as_of": "2026-07-14", "source": "https://developers.openai.com/api/docs/pricing", "value": 0.2510425499999998, "assumption": "OpenAI Standard API rates; gpt-4o-mini input treated as uncached because cached-token detail is not logged by this runner.", "breakdown": {"token_models": {"gpt-4o-mini": 0.22349564999999982}, "gpt-4o-mini-transcribe": 0.0275469}}`

## Representative transcript cases

| Audio ID | Outcome | Raw | Corrected | Reference |
|---:|---|---|---|---|
| 112 | improved | Nếu sinh viên không nhớ pass nhưng còn gờ mail thì làm gì? | Nếu sinh viên không nhớ pass nhưng còn Gmail thì làm gì? | Nếu sinh viên không nhớ pass nhưng còn Gmail thì làm gì? |
| 159 | improved | Nếu sinh viên giữ lại Wi-Fi khác ngoài FPT Exam thì sao? | Nếu sinh viên giữ lại WiFi khác ngoài FPT Exam thì sao? | Nếu sinh viên giữ lại WiFi khác ngoài FU-Exam thì sao? |
| 192 | improved | Giám thị có thể chi cập Network and Internet setting từ đâu trên tab 3? | Giám thị có thể chi cập Network and Internet settings từ đâu trên tab 3? | GT có thể truy cập Network & Internet settings từ đâu trên Taskbar? |
| 102 | unchanged | Bước một của quy trình reset là gì? | Bước một của quy trình reset là gì? | Bước 1 của quy trình reset là gì? |
| 103 | unchanged | Sau khi nhập thông tin ở bước một, điều gì xảy ra? | Sau khi nhập thông tin ở bước một, điều gì xảy ra? | Sau khi nhập thông tin ở bước 1 điều gì xảy ra? |
| 104 | unchanged | Mật khẩu mới được gửi đến đâu? | Mật khẩu mới được gửi đến đâu? | Mật khẩu mới được gửi đến đâu? |
| 127 | degraded | Mật khẩu nhận từ email có phải mật khẩu cuối cùng không? | Mật khẩu nhận từ Gmail có phải mật khẩu cuối cùng không? | Mật khẩu nhận từ email có phải mật khẩu cuối cùng không? |
| 152 | degraded | Bước đầu tiên để forget WiFi là gì? | Bước đầu tiên để quên WiFi là gì? | Bước đầu tiên để Forget WiFi là gì? |
| 158 | degraded | giám thị cần kiểm tra tình trạng forget wifi khi nào? | giám thị cần kiểm tra tình trạng quên WiFi khi nào? | Giám thị cần kiểm tra tình trạng Forget WiFi khi nào? |

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

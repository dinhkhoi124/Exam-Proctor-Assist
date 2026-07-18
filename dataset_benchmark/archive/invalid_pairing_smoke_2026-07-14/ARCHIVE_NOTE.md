# Invalid pairing smoke archive — 2026-07-14

This directory contains runtime outputs from the first five-sample smoke run.
They are retained only for auditability and must not be used as benchmark evidence.

## Reason for invalidation

The run used audio IDs `5, 13, 16, 20, 23`. Subsequent manual inspection found
that workbook rows `1–100` in `AUDIO_299.xlsx` do not align with equivalently
numbered WAV files. The resulting references were therefore incorrect for the
audio being evaluated (`audio_reference_mismatch`).

The observed WER, retrieval, answer, judge, latency and report outputs from this
run are scientifically invalid because the ground truth pairing was wrong.

## Resolution

- Dataset v1 admits only the independently cross-checked aligned range `101–230`.
- A deterministic 20-sample validation (seed `44`) confirmed the retained range:
  20/20 successful STT results, all WER below `0.5`, mean WER `0.08256`.
- Dataset v1 is rebuilt and split from the 130 retained pairs only.
- IDs `1–100` must not be restored without an independently supplied, human-
  verified mapping or replacement reference transcript set.

The validation checkpoint remains outside this archive at
`benchmark_outputs/alignment_check_101_230.jsonl`.

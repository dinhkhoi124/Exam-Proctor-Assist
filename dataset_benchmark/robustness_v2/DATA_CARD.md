# Data Card

## Dataset identity

This benchmark derives from the Vietnamese FPT support corpus and stores a
frozen, hash-addressed base snapshot inside the v2 namespace. The evaluated
pilot contains 10 independent base utterances, 10 C0 audio variants, 30
pipeline records, and one speaker (`Toàn`).

## Intended use

The dataset supports controlled comparison of raw, always-corrected, and
selectively corrected ASR text before retrieval and answer generation. It is
appropriate for engineering diagnostics and regression checks, not for claims
about population-wide or real-environment robustness.

## Splits and dependencies

Dev/test membership is assigned after normalized and near-semantic clustering.
The split is leakage-audited, but it is regrouped from previously observed v1
data and therefore is not a fresh independent test. Synthetic noise/RIR recipes
have split-scoped seeds, donors, sources, crops, and hashes.

## Labels and missing evidence

References come from the restored UTF-8 manifest and are input-hashed. Current
answer workbooks contain no completed human scores, error workbooks contain no
reviewed taxonomy/recoverability labels, and the manifest has no gold relevance
pages for these pilot rows. These fields are reported as unavailable.

## Limitations and risks

- One speaker and ten clean utterances do not cover speaker or acoustic diversity.
- No C1-C3 inference is included in the current report.
- Synthetic degradation cannot establish real-world performance.
- Audio variants share base content and must not be counted as independent.
- Text correction cannot recover information absent from the 1-best transcript.
- Private transcripts and document context are not sent to external APIs.

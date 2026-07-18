# Dev prompt iteration 001 — rejected 2026-07-14

This snapshot is a valid five-sample dev run on dataset
`v1-aligned-101-230`, IDs `101, 109, 114, 121, 122`. The audio/reference
pairing is valid, but the correction prompt iteration was rejected during prompt
development and must not be reported as a final test result.

Run correction prompt hash:
`34893ac64f9f8c5e38b6795855334a7a57853a6dbb8f61168e52869da0a352b5`.

## Rejection evidence

- Baseline WER: `0.03774`
- Proposed WER: `0.20755`
- Absolute WER reduction: `-0.16981` (degradation)
- Outcomes: 4 degraded, 1 unchanged, 0 improved
- Change precision: `0.0`
- Over-correction rate: `0.75`
- Baseline/proposed proxy Jaccard@5: `0.72 / 0.57714`

Observed failure modes included stylistic paraphrasing (`dùng` → `sử dụng`),
adding unstated filler (`phải`), expanding an already valid `pass`, translating
the product token `Student`, and failing to recover the domain term `EOS/PEA`
from a likely ASR confusion.

The next prompt iteration enforces minimal span edits, preservation of valid
abbreviations/product tokens, and conservative domain-glossary correction. Raw
STT remains cached and is reused; prompt development uses dev data only.

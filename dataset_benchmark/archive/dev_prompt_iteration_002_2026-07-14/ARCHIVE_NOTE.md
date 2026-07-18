# Dev prompt iteration 002 — rejected 2026-07-14

Valid five-sample dev run on dataset `v1-aligned-101-230`, IDs
`101, 109, 114, 121, 122`. This iteration is retained for prompt-development
audit only and is not a final test result.

Correction prompt hash:
`01b08c57571986352b0372b2179ded675dc0c48508b7be5ac9708f0b38068421`.

## Result

- Baseline/proposed WER: `0.03774 / 0.07547`
- Absolute WER reduction: `-0.03774` (degradation)
- Outcomes: 1 improved, 2 unchanged, 2 degraded
- Change precision: `0.3333`
- Error-correction recall: `1.0`
- Over-correction rate: `0.5`
- Baseline/proposed proxy Jaccard@5: `0.72 / 0.65333`

The iteration correctly recovered `BAA` as `EOS/PEA`, but still performed an
explicitly prohibited synonym rewrite (`dùng` → `sử dụng`) and incorrectly
converted the valid Vietnamese phrase `sinh viên` to `Students`. Iteration 003
therefore replaces the long rule list with a shorter copy-edit protocol and
explicit KEEP/FIX examples. Raw STT remains unchanged and cached.

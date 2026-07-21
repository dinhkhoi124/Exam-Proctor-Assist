# ASR Correction Robustness Benchmark v2 Report

## Executive summary

This report's primary evidence is the **held-out test subset of owner-recorded environmental noise**. Main metric tables exclude development and clean C0 rows. P0 uses raw STT, P1 always requests correction, and P2 uses the locked selective detector.

- P0/P1/P2 corpus WER: 16.59% / 16.62% / 16.59%.
- Aggregate transcript WER differs among pipelines; inspect paired statistics and strata.
- Treat owner-recorded mixtures as controlled recorded-noise evidence, not unconstrained field deployment evidence.
- Neither P1 nor P2 is recommended for production from this run.

## Evidence layers

| Layer | Scope | Role in main tables |
|---|---|---|
| Held-out recorded-noise test | 104 bases; 416 variants; 1248 pipeline rows | Included |
| Development + clean C0 | 702 pipeline rows | Excluded; secondary diagnostics |
| Historical synthetic run | Prior run | Excluded; not pooled |

## Dataset

- Independent base utterances: 104
- Evaluated base IDs: 101–228 (104 total)
- Selection: all eligible test base IDs and recorded-noise variants; ordering: manifest order after locked primary-evidence filter; randomized: False.
- Primary audio variants: 416
- Primary pipeline records: 1248
- Full run audio variants: 650
- Full run pipeline records: 1950
- Independent test noise sources: 28
- Speakers: 2 (Toàn, Trí)
- Conditions: C1, C2, C3
- Noise/severity: owner-recorded fan, cafe, office, and speech-babble mixed at locked 0/5/10/15 dB target SNR.
- Split: semantic-cluster regrouped research split; not fresh test.
- Leakage audit: clean.

## Transcript results

| Pipeline | Corpus WER | Macro WER | Corpus CER | Improved | Unchanged | Degraded |
|---|---:|---:|---:|---:|---:|---:|
| P0 | 16.59% | 17.12% | 11.67% | 0 | 416 | 0 |
| P1 | 16.62% | 17.13% | 11.94% | 11 | 391 | 14 |
| P2 | 16.59% | 17.12% | 11.67% | 0 | 416 | 0 |

Hallucinated-token and semantic-rewrite values in the JSON/CSV are lexical proxies. Human taxonomy/recoverability is unavailable because no error rows are marked reviewed.

## Retrieval results

| Pipeline | Proxy Jaccard@5 | Proxy overlap recall@5 | True gold |
|---|---:|---:|---|
| P0 | 55.18% | 59.19% | unavailable |
| P1 | 57.18% | 61.08% | unavailable |
| P2 | 55.18% | 59.19% | unavailable |

Proxy retrieval compares selected pages with retrieval from the reference transcript. It is not relevance ground truth and is not mixed with the empty true-gold section.

## Final answer results

- Human evaluation: unavailable (Answer grading workbooks contain no scores.)
- LLM judge: available (1248 scored rows); auxiliary only.
- Cached answers are expected for all 1248 pipeline records, but ungraded answers are not counted as correctness, faithfulness, completeness, citation quality, or task-success evidence.

| Pipeline | Judge correctness | Groundedness | Helpfulness | Safety |
|---|---:|---:|---:|---:|
| P0 | 4.204 | 4.385 | 4.226 | 4.591 |
| P1 | 4.192 | 4.428 | 4.245 | 4.611 |
| P2 | 4.188 | 4.399 | 4.214 | 4.599 |

Judge scores are auxiliary and do not satisfy the human task-success criterion.

## Selective correction

- Detector: heuristic_v1
- Threshold: 0.6
- Decisions: `{"use_raw": 650}`
- Trigger reasons: `{"domain_entity_or_acronym": 139, "short_transcript": 1, "number_ip_or_version": 2}`
- P1 logical correction call rate: 100.00%
- P2 logical correction call rate: 0.00%
- Detector precision/recall remains unavailable without oracle risk labels.

## Operational metrics

| Pipeline | Retrieval p50 | Retrieval p95 | Fresh API calls | Fresh cost |
|---|---:|---:|---:|---:|
| P0 | 926.0 ms | 2646.2 ms | 1485 | $0.9987/1k requests |
| P1 | 929.5 ms | 2632.5 ms | 1996 | $1.0328/1k requests |
| P2 | 887.0 ms | 2707.0 ms | 1485 | $1.0011/1k requests |

Unique fresh API spend for the full experimental run was $1.696573. Each route cost includes observed STT plus route-specific correction, answer, and auxiliary judge cost; route totals must not be summed. Compatible C0 imports incurred no fresh cost. Provider billing remains authoritative.

End-to-end latency is not reconstructed by this evaluator; component cache latencies and the strict local-inference audit remain the authoritative artifacts.

## Statistics

Primary resampling unit: `base_id` (N=104).
- P1−P0 mean WER difference: 0.000039; 95% cluster-bootstrap CI [-0.004611, 0.004865]; Wilcoxon p=0.9553; rank-biserial=-0.0143; Holm-adjusted p=1.0000.
- P2−P0 mean WER difference: 0.000000; 95% cluster-bootstrap CI [0.000000, 0.000000]; Wilcoxon p=1.0000; rank-biserial=0.0000; Holm-adjusted p=1.0000.

Interpret paired differences with cluster-bootstrap intervals, effect sizes, and condition strata.

## Stratified reporting

Machine-readable stratification is provided for condition, noise, SNR, speaker, intent, semantic cluster, raw-WER bin, code-switch, and entity flags.
Held-out recorded-noise type/SNR/source strata are populated. Recoverability and taxonomy strata remain unavailable pending annotation.

## Noise-source sensitivity

- P1: 104 base clusters; 28 noise-source clusters; two-way bootstrap 95% CI [-0.007079, 0.007075].
- P2: 104 base clusters; 28 noise-source clusters; two-way bootstrap 95% CI [0.000000, 0.000000].
Base-cluster and noise-source sensitivity are reported separately; variants sharing a recording are not treated as independent sources.

## Failure analysis

- Correction success with transcript improvement: 11/416.
- Correction unchanged: 391/416.
- Over-correction/degraded: 14/416.
- Retrieval improved while WER unchanged: 0 observed.
- WER improved while retrieval worsened: 0 observed.
- Audio-only irrecoverable errors: unavailable pending recoverability labels.

## Production decision matrix

| Pipeline | Clean WER NI | Task success | True-gold retrieval | Call rate | New speakers | Recommend |
|---|---|---|---|---|---|---|
| P1 | pass | unavailable | unavailable | fail | fail | No |
| P2 | pass | unavailable | unavailable | pass | fail | No |

Production remains unchanged; this report never enables a mode automatically.

## Limitations

- Primary evidence is held-out test recorded-noise only; development and clean rows are secondary.
- Synthetic augmentation is not equivalent to recorded environmental audio.
- Audio variants are clustered by base_id and are not independent samples.
- Retrieval agreement is a reference-query proxy, not relevance ground truth.
- Human answer grading, error taxonomy, and recoverability annotations are unavailable.
- Text-only correction is limited by the ASR information bottleneck.
- Results must not be generalized to other domains or new speakers.
- Short recorded clips are deterministically wrapped when shorter than an utterance; source-level sensitivity is reported.

## Reproducibility

- Config hash: `c2737172719a73a1123397ce892e392bc0fb87ffa4ea88aa725fae2c0ddda72d`
- Machine-readable summary, metrics CSV, sample CSV, and base CSV are stored beside this report.

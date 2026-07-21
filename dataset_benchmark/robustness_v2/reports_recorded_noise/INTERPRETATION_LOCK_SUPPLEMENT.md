# Interpretation Lock Supplement - Recorded Noise Benchmark

Source artifacts:

- Summary: `dataset_benchmark/robustness_v2/reports_recorded_noise/robustness_v2_recorded_noise_summary.json`
- Sample-level CSV: `dataset_benchmark/robustness_v2/reports_recorded_noise/robustness_v2_recorded_noise_sample_level.csv`
- Strict audit: `dataset_benchmark/robustness_v2/reports_recorded_noise/local_inference_audit.json`

Primary evidence scope: 104 held-out test base utterances, 416 owner-recorded environmental-noise variants, 28 held-out test noise-source recordings, and 1248 pipeline rows.

## 1. P2 Selective Correction

P2 is selective correction under the configured `heuristic_v1` risk detector with threshold `0.6`.

On the 416 primary held-out recorded-noise test variants:

| Pipeline | Corpus WER | Improved | Unchanged | Degraded | Correction call rate |
|---|---:|---:|---:|---:|---:|
| P0 raw | 0.1658711217 | 0 | 416 | 0 | 0% |
| P2 selective | 0.1658711217 | 0 | 416 | 0 | 0% |

P2 risk decisions on primary rows:

| Decision | Rows |
|---|---:|
| use_raw | 416 |

Across the full 650-variant run, selective decision counts were also `use_raw: 650`. Therefore P2 is exactly equivalent to P0 in this recorded-noise run. This matches the clean pilot behavior directionally: the detector did not trigger correction under the current threshold/rules, so P2 makes no correction calls and cannot improve or degrade transcript WER.

P2 vs P0 statistics for mean WER:

| Test | Result |
|---|---:|
| Base bootstrap candidate_minus_p0 | 0.0 |
| Base bootstrap 95% CI | [0.0, 0.0] |
| Base bootstrap unit/count | base_id / 104 |
| Base bootstrap iterations/seed | 5000 / 20260718 |
| Wilcoxon p-value | 1.0 |
| Rank-biserial | 0.0 |
| All differences zero | true |
| Holm-adjusted p-value | 1.0 |

P2 two-way bootstrap and source sensitivity:

| Test | Result |
|---|---:|
| Two-way bootstrap method | pigeonhole_two_way_cluster_bootstrap |
| Clusters | base_id x noise_source_recording_id |
| Cluster counts | 104 x 28 |
| Samples | 416 |
| Iterations/seed | 5000 / 20260720 |
| Mean difference | 0.0 |
| 95% CI | [0.0, 0.0] |
| Leave-one-noise-source-out min/max mean difference | [0.0, 0.0] |

## 2. Over-Correction Definition

The reported P1 over-correction rate `0.0264900662` is computed as:

`count(rows where P0 raw_word_errors == 0 and P1 word_errors > 0) / count(rows where P0 raw_word_errors == 0)`

For the 416 primary rows:

| Quantity | Count |
|---|---:|
| Originally correct under P0 | 151 |
| Over-corrected by P1 | 4 |
| P1 over-correction rate | 4 / 151 = 0.0264900662 |
| P1 degraded rows total | 14 |
| Over-corrected rows that are degraded | 4 / 4 |
| P1 improved rows total | 11 |

So over-correction is a subset of degraded rows, not all degraded rows. The `2.649%` rate corresponds to 4 rows, not 11 rows. Its visual similarity to the `11` improved rows is coincidental, not a column mix-up.

Primary P1 over-corrected variant IDs:

- `127_c2_v01_recorded_cafe`
- `127_c3_v01_recorded_speech_babble`
- `158_c2_v01_recorded_cafe`
- `158_c3_v01_recorded_speech_babble`

Primary P1 improved variant IDs:

- `112_c3_v01_recorded_speech_babble`
- `117_c2_v01_recorded_cafe`
- `120_c1_v01_recorded_fan`
- `122_c3_v01_recorded_speech_babble`
- `159_c2_v01_recorded_cafe`
- `159_c3_v01_recorded_speech_babble`
- `176_c3_v01_recorded_speech_babble`
- `179_c3_v01_recorded_speech_babble`
- `189_c3_v01_recorded_speech_babble`
- `196_c1_v01_recorded_fan`
- `203_c2_v02_recorded_office`

## 3. P1 Two-Way Bootstrap and Noise-Source Sensitivity

P1 vs P0 mean WER:

| Test | Result |
|---|---:|
| Base bootstrap candidate_minus_p0 | 0.0000390502 |
| Base bootstrap 95% CI | [-0.0046110140, 0.0048647800] |
| Base bootstrap unit/count | base_id / 104 |
| Base bootstrap iterations/seed | 5000 / 20260718 |
| Wilcoxon p-value | 0.9553348263 |
| Rank-biserial | -0.0142857143 |
| Holm-adjusted p-value | 1.0 |

P1 two-way bootstrap and source sensitivity:

| Test | Result |
|---|---:|
| Two-way bootstrap method | pigeonhole_two_way_cluster_bootstrap |
| Clusters | base_id x noise_source_recording_id |
| Cluster counts | 104 x 28 |
| Samples | 416 |
| Iterations/seed | 5000 / 20260719 |
| Mean difference | 0.0000390502 |
| 95% CI | [-0.0070792895, 0.0070748378] |
| Leave-one-noise-source-out min/max mean difference | [-0.0006822011, 0.0011120407] |

Interpretation: the two-way CI is wider than the base-only CI, as expected when respecting both base utterance and noise-source dependence. It still crosses zero cleanly. Leave-one-noise-source-out does not reveal a single held-out noise recording that flips the conclusion into a material win for P1.

## 4. Breakdown by Noise Category

Each noise category contributes 104 primary test variants.

| Noise type | P0 WER | P1 WER | P1 improved | P1 unchanged | P1 degraded | P1 relative WER reduction | P2 WER | P2 improved | P2 unchanged | P2 degraded |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cafe | 0.1491646778 | 0.1503579952 | 2 | 99 | 3 | -0.0080000000 | 0.1491646778 | 0 | 104 | 0 |
| fan | 0.1169451074 | 0.1205250597 | 2 | 98 | 4 | -0.0306122449 | 0.1169451074 | 0 | 104 | 0 |
| office | 0.1443914081 | 0.1503579952 | 1 | 99 | 4 | -0.0413223140 | 0.1443914081 | 0 | 104 | 0 |
| speech_babble | 0.2529832936 | 0.2434367542 | 6 | 95 | 3 | 0.0377358491 | 0.2529832936 | 0 | 104 | 0 |

Interpretation: P1 shows a small positive signal only on `speech_babble`, while it is negative on `fan`, `cafe`, and `office`. Because each stratum has only 104 variants and the global two-way/bootstrap evidence does not support a significant improvement, this is a hypothesis for future targeted work, not a defensible global win.


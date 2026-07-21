# Methodology

## Scope

The current result is a 10-base, one-speaker C0 pilot comparing three routes:
P0 uses raw STT, P1 always applies text correction, and P2 applies correction
only when the locked heuristic detector reaches its threshold. C1-C3 generated
audio is not evaluated in this checkpoint.

## Units and metrics

The independent unit is `base_id`; augmented variants and pipeline routes are
correlated observations. Transcript reporting includes corpus and macro WER,
CER, relative WER reduction, improved/unchanged/degraded counts, lexical
hallucination proxy, semantic-rewrite proxy, change precision, correction
recall, and over-correction rate. Undefined denominators are reported as
unavailable rather than zero.

Retrieval reference-query agreement is reported only as a proxy. True relevance
metrics require independently annotated gold pages and remain unavailable.
Human answer preference is primary; the disabled LLM judge is auxiliary only.

## Statistical analysis

Paired differences are calculated per `base_id`. Confidence intervals use a
5,000-iteration cluster bootstrap with seed 20260718. Paired Wilcoxon tests and
rank-biserial effect sizes accompany point estimates, with Holm correction
across candidate comparisons. The clean C0 non-inferiority WER margin is 0.005.

## Provenance and leakage controls

Each stage records absolute input paths, SHA-256 values, sizes, output hashes,
and the canonical config hash. V2 writes only below `robustness_v2`. Split
grouping and augmentation asset/donor auditing are inherited from Priority 2;
the regrouped split is research evidence and not a fresh locked test.

## Decision rule

No metric automatically changes production. A candidate must satisfy the full
decision matrix, including true-gold retrieval, human task success, degraded
conditions, latency, correction-call rate, speaker diversity, and safety.
Missing evidence fails readiness but is not converted into a negative score.

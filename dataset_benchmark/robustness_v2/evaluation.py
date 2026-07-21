"""Cluster-aware metrics for robustness-v2 pipeline outputs."""

from __future__ import annotations

from collections import Counter, defaultdict
import math
import random
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

from dataset_benchmark.scripts.metrics import (
    normalize_text,
    page_key,
    transcript_errors,
    true_retrieval_metrics,
)


def percentile(values: Sequence[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def wer_bin(value: float) -> str:
    if value == 0:
        return "WER = 0"
    if value <= 0.05:
        return "0 < WER <= 5%"
    if value <= 0.15:
        return "5% < WER <= 15%"
    if value <= 0.30:
        return "15% < WER <= 30%"
    return "WER > 30%"


def page_overlap(pages: Sequence[dict], reference_pages: Sequence[dict], k: int = 5) -> dict:
    predicted = {page_key(item) for item in pages[:k]}
    reference = {page_key(item) for item in reference_pages[:k]}
    union = predicted | reference
    return {
        "jaccard_at_5_proxy": len(predicted & reference) / len(union) if union else 1.0,
        "overlap_recall_at_5_proxy": (
            len(predicted & reference) / len(reference) if reference else 1.0
        ),
    }


def code_switch_flag(text: str) -> bool:
    terms = {
        "account", "password", "wifi", "reset", "login", "email", "server",
        "fail", "vpn", "username", "oldpass", "newpass", "student",
    }
    tokens = set(normalize_text(text).split())
    return bool(tokens & terms)


def entity_flag(text: str) -> bool:
    folded = text.casefold()
    return any(
        token in folded
        for token in ("eos", "pea", "e360", "fu-exam", "wifi", "vpn", "k19", "k21")
    )


def hallucinated_token_rate(reference: str, hypothesis: str) -> float:
    reference_counts = Counter(normalize_text(reference).split())
    hypothesis_tokens = normalize_text(hypothesis).split()
    remaining = Counter(reference_counts)
    hallucinated = 0
    for token in hypothesis_tokens:
        if remaining[token]:
            remaining[token] -= 1
        else:
            hallucinated += 1
    return hallucinated / len(hypothesis_tokens) if hypothesis_tokens else 0.0


def aggregate_transcript_pipeline(rows: Sequence[Mapping[str, Any]]) -> dict:
    if not rows:
        return {"samples": 0, "availability": "unavailable"}
    word_errors = sum(int(row["word_errors"]) for row in rows)
    reference_words = sum(int(row["reference_words"]) for row in rows)
    char_errors = sum(int(row["char_errors"]) for row in rows)
    reference_chars = sum(int(row["reference_chars"]) for row in rows)
    outcomes = Counter(str(row["outcome_vs_p0"]) for row in rows)
    changed = [row for row in rows if row["transcript_changed_vs_p0"]]
    raw_error = [row for row in rows if int(row["raw_word_errors"]) > 0]
    originally_correct = [row for row in rows if int(row["raw_word_errors"]) == 0]
    corpus_wer = word_errors / max(1, reference_words)
    raw_corpus_wer = sum(int(row["raw_word_errors"]) for row in rows) / max(
        1, reference_words
    )
    return {
        "availability": "available",
        "samples": len(rows),
        "independent_base_utterances": len({int(row["base_id"]) for row in rows}),
        "corpus_wer": corpus_wer,
        "macro_wer": mean(float(row["wer"]) for row in rows),
        "corpus_cer": char_errors / max(1, reference_chars),
        "improved_count": outcomes["improved"],
        "unchanged_count": outcomes["unchanged"],
        "degraded_count": outcomes["degraded"],
        "relative_wer_reduction_vs_p0": (
            (raw_corpus_wer - corpus_wer) / raw_corpus_wer if raw_corpus_wer else 0.0
        ),
        "change_precision": (
            sum(row["outcome_vs_p0"] == "improved" for row in changed) / len(changed)
            if changed
            else 0.0
        ),
        "error_correction_recall": (
            sum(row["outcome_vs_p0"] == "improved" for row in raw_error) / len(raw_error)
            if raw_error
            else 0.0
        ),
        "over_correction_rate": (
            sum(int(row["word_errors"]) > 0 for row in originally_correct)
            / len(originally_correct)
            if originally_correct
            else 0.0
        ),
        "hallucinated_token_rate_proxy": mean(
            float(row["hallucinated_token_rate_proxy"]) for row in rows
        ),
        "semantic_rewrite_rate_proxy": mean(
            float(row["semantic_rewrite_proxy"]) for row in rows
        ),
        "proxy_disclosure": (
            "Hallucinated-token and semantic-rewrite rates are lexical proxies, "
            "not human error-taxonomy labels."
        ),
    }


def aggregate_retrieval_pipeline(rows: Sequence[Mapping[str, Any]]) -> dict:
    proxy_rows = [row for row in rows if row.get("retrieval_proxy_available")]
    gold_rows = [row for row in rows if row.get("retrieval_gold_available")]
    output = {
        "proxy": {
            "availability": "available" if proxy_rows else "unavailable",
            "samples": len(proxy_rows),
            "jaccard_at_5": (
                mean(float(row["jaccard_at_5_proxy"]) for row in proxy_rows)
                if proxy_rows
                else None
            ),
            "overlap_recall_at_5": (
                mean(float(row["overlap_recall_at_5_proxy"]) for row in proxy_rows)
                if proxy_rows
                else None
            ),
            "disclosure": "Reference-query agreement proxy; not relevance ground truth.",
        },
        "true_gold": {
            "availability": "available" if gold_rows else "unavailable",
            "samples": len(gold_rows),
            "reason": None if gold_rows else "No adjudicated source/page gold for evaluated rows.",
        },
    }
    if gold_rows:
        for metric in (
            "hit_at_1", "hit_at_3", "hit_at_5", "mrr_at_10", "recall_at_5", "ndcg_at_5"
        ):
            output["true_gold"][metric] = mean(float(row[metric]) for row in gold_rows)
    return output


def aggregate_operational_pipeline(rows: Sequence[Mapping[str, Any]]) -> dict:
    if not rows:
        return {"availability": "unavailable", "samples": 0}
    retrieval_latencies = [float(row["retrieval_latency_ms"]) for row in rows]
    correction_requested = [bool(row["correction_requested"]) for row in rows]
    correction_api = [bool(row["correction_api_call"]) for row in rows]
    answer_api = [bool(row["answer_api_call"]) for row in rows]
    return {
        "availability": "partial",
        "samples": len(rows),
        "stt_latency": {"availability": "unavailable_imported_cache"},
        "correction_latency": {"availability": "unavailable_imported_cache"},
        "retrieval_latency_ms": {
            "p50": percentile(retrieval_latencies, 0.50),
            "p95": percentile(retrieval_latencies, 0.95),
        },
        "final_answer_latency": {"availability": "unavailable_imported_cache"},
        "end_to_end_latency": {"availability": "unavailable_imported_components"},
        "logical_correction_call_rate": sum(correction_requested) / len(rows),
        "fresh_correction_api_call_rate": sum(correction_api) / len(rows),
        "fallback_rate": sum(row["query_source"] == "raw_fallback" for row in rows) / len(rows),
        "api_error_rate": sum(row["answer_status"] == "failed" for row in rows) / len(rows),
        "fresh_answer_api_call_rate": sum(answer_api) / len(rows),
        # Filled by the evaluator from the stage caches and locked pricing config.
        "fresh_api_cost_usd": None,
        "fresh_api_cost_per_1000_requests_usd": None,
        "historical_imported_prompt_tokens": sum(int(row.get("prompt_tokens") or 0) for row in rows),
        "historical_imported_completion_tokens": sum(
            int(row.get("completion_tokens") or 0) for row in rows
        ),
    }


def base_aggregates(sample_rows: Sequence[Mapping[str, Any]]) -> list[dict]:
    grouped: dict[tuple[int, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in sample_rows:
        grouped[(int(row["base_id"]), str(row["pipeline"]))].append(row)
    output = []
    for (base_id, pipeline), rows in sorted(grouped.items()):
        output.append(
            {
                "base_id": base_id,
                "pipeline": pipeline,
                "variants": len(rows),
                "mean_wer": mean(float(row["wer"]) for row in rows),
                "mean_cer": mean(float(row["cer"]) for row in rows),
                "mean_retrieval_jaccard_proxy": mean(
                    float(row["jaccard_at_5_proxy"])
                    for row in rows
                    if row.get("retrieval_proxy_available")
                ) if any(row.get("retrieval_proxy_available") for row in rows) else None,
            }
        )
    return output


def paired_base_values(
    base_rows: Sequence[Mapping[str, Any]], metric: str, baseline: str, candidate: str
) -> tuple[list[float], list[float], list[int]]:
    indexed = {(int(row["base_id"]), row["pipeline"]): row for row in base_rows}
    base_ids = sorted(
        base_id
        for base_id, pipeline in indexed
        if pipeline == baseline and (base_id, candidate) in indexed
        and indexed[(base_id, baseline)].get(metric) is not None
        and indexed[(base_id, candidate)].get(metric) is not None
    )
    return (
        [float(indexed[(base_id, baseline)][metric]) for base_id in base_ids],
        [float(indexed[(base_id, candidate)][metric]) for base_id in base_ids],
        base_ids,
    )


def cluster_bootstrap(
    baseline: Sequence[float], candidate: Sequence[float], *, iterations: int, seed: int
) -> dict:
    if not baseline or len(baseline) != len(candidate):
        return {"availability": "unavailable"}
    differences = [cand - base for base, cand in zip(baseline, candidate)]
    rng = random.Random(seed)
    draws = [
        mean(rng.choice(differences) for _ in differences) for _ in range(iterations)
    ]
    draws.sort()
    return {
        "availability": "available",
        "unit": "base_id",
        "independent_base_utterances": len(differences),
        "candidate_minus_p0": mean(differences),
        "ci_low": draws[int(iterations * 0.025)],
        "ci_high": draws[min(iterations - 1, int(iterations * 0.975))],
        "iterations": iterations,
        "seed": seed,
    }


def two_way_cluster_bootstrap(
    rows: Sequence[Mapping[str, Any]],
    *,
    value_field: str,
    first_cluster: str,
    second_cluster: str,
    iterations: int,
    seed: int,
) -> dict:
    """Pigeonhole bootstrap for observations crossed by two dependency sources."""

    if not rows:
        return {"availability": "unavailable", "samples": 0}
    first_values = sorted({str(row[first_cluster]) for row in rows})
    second_values = sorted({str(row[second_cluster]) for row in rows})
    rng = random.Random(seed)
    estimates = []
    for _ in range(iterations):
        first_weights = Counter(rng.choices(first_values, k=len(first_values)))
        second_weights = Counter(rng.choices(second_values, k=len(second_values)))
        weighted_sum = 0.0
        total_weight = 0
        for row in rows:
            weight = (
                first_weights[str(row[first_cluster])]
                * second_weights[str(row[second_cluster])]
            )
            weighted_sum += weight * float(row[value_field])
            total_weight += weight
        if total_weight:
            estimates.append(weighted_sum / total_weight)
    observed = mean(float(row[value_field]) for row in rows)
    return {
        "availability": "available" if estimates else "unavailable",
        "method": "pigeonhole_two_way_cluster_bootstrap",
        "clusters": [first_cluster, second_cluster],
        "first_cluster_count": len(first_values),
        "second_cluster_count": len(second_values),
        "samples": len(rows),
        "iterations": iterations,
        "seed": seed,
        "mean_difference": observed,
        "ci_low": percentile(estimates, 0.025) if estimates else None,
        "ci_high": percentile(estimates, 0.975) if estimates else None,
    }


def paired_wilcoxon(baseline: Sequence[float], candidate: Sequence[float]) -> dict:
    if not baseline or len(baseline) != len(candidate):
        return {"availability": "unavailable"}
    differences = [cand - base for base, cand in zip(baseline, candidate)]
    nonzero = [delta for delta in differences if delta != 0]
    if not nonzero:
        return {
            "availability": "available",
            "p_value": 1.0,
            "rank_biserial": 0.0,
            "all_differences_zero": True,
        }
    try:
        from scipy.stats import rankdata, wilcoxon

        result = wilcoxon(candidate, baseline, zero_method="wilcox")
        ranks = rankdata([abs(delta) for delta in nonzero])
        positive = sum(rank for rank, delta in zip(ranks, nonzero) if delta > 0)
        negative = sum(rank for rank, delta in zip(ranks, nonzero) if delta < 0)
        return {
            "availability": "available",
            "p_value": float(result.pvalue),
            "rank_biserial": float((positive - negative) / (positive + negative)),
            "all_differences_zero": False,
        }
    except (ImportError, ValueError) as exc:
        return {"availability": "unavailable", "reason": str(exc)}


def holm_adjust(p_values: Mapping[str, float | None]) -> dict[str, float | None]:
    available = sorted(
        ((name, float(value)) for name, value in p_values.items() if value is not None),
        key=lambda item: item[1],
    )
    total = len(available)
    adjusted: dict[str, float | None] = {name: None for name in p_values}
    running = 0.0
    for index, (name, value) in enumerate(available):
        running = max(running, min(1.0, value * (total - index)))
        adjusted[name] = running
    return adjusted


def stratify(rows: Sequence[Mapping[str, Any]], field: str) -> dict:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(field) if row.get(field) not in (None, "") else "unknown")].append(row)
    return {
        value: {
            pipeline: aggregate_transcript_pipeline(
                [row for row in group if row["pipeline"] == pipeline]
            )
            for pipeline in ("P0", "P1", "P2")
        }
        for value, group in sorted(groups.items())
    }

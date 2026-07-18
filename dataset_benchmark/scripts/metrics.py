from __future__ import annotations

from collections import Counter
import math
import random
import re
import unicodedata
from typing import Iterable, Sequence


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text or "").casefold()
    normalized = "".join(
        " " if unicodedata.category(char).startswith("P") else char
        for char in normalized
    )
    return re.sub(r"\s+", " ", normalized).strip()


def edit_distance(reference: Sequence, hypothesis: Sequence) -> int:
    previous = list(range(len(hypothesis) + 1))
    for ref_index, ref_item in enumerate(reference, start=1):
        current = [ref_index]
        for hyp_index, hyp_item in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[hyp_index] + 1,
                    previous[hyp_index - 1] + (ref_item != hyp_item),
                )
            )
        previous = current
    return previous[-1]


def transcript_errors(reference: str, hypothesis: str) -> dict:
    normalized_reference = normalize_text(reference)
    normalized_hypothesis = normalize_text(hypothesis)
    reference_words = normalized_reference.split()
    hypothesis_words = normalized_hypothesis.split()
    word_errors = edit_distance(reference_words, hypothesis_words)
    char_reference = normalized_reference.replace(" ", "")
    char_hypothesis = normalized_hypothesis.replace(" ", "")
    char_errors = edit_distance(char_reference, char_hypothesis)
    return {
        "word_errors": word_errors,
        "reference_words": len(reference_words),
        "wer": word_errors / max(1, len(reference_words)),
        "char_errors": char_errors,
        "reference_chars": len(char_reference),
        "cer": char_errors / max(1, len(char_reference)),
        "exact_match": normalized_reference == normalized_hypothesis,
    }


def aggregate_transcripts(rows: list[dict]) -> dict:
    baseline_word_errors = sum(row["baseline_word_errors"] for row in rows)
    proposed_word_errors = sum(row["proposed_word_errors"] for row in rows)
    reference_words = sum(row["reference_words"] for row in rows)
    baseline_char_errors = sum(row["baseline_char_errors"] for row in rows)
    proposed_char_errors = sum(row["proposed_char_errors"] for row in rows)
    reference_chars = sum(row["reference_chars"] for row in rows)
    baseline_wer = baseline_word_errors / max(1, reference_words)
    proposed_wer = proposed_word_errors / max(1, reference_words)
    baseline_cer = baseline_char_errors / max(1, reference_chars)
    proposed_cer = proposed_char_errors / max(1, reference_chars)

    changed = [row for row in rows if row["changed"]]
    erroneous = [row for row in rows if row["baseline_word_errors"] > 0]
    originally_correct = [row for row in rows if row["baseline_word_errors"] == 0]
    counts = Counter(row["outcome"] for row in rows)
    return {
        "samples": len(rows),
        "baseline_wer": baseline_wer,
        "proposed_wer": proposed_wer,
        "absolute_wer_reduction": baseline_wer - proposed_wer,
        "relative_wer_reduction": (
            (baseline_wer - proposed_wer) / baseline_wer if baseline_wer else 0.0
        ),
        "baseline_cer": baseline_cer,
        "proposed_cer": proposed_cer,
        "absolute_cer_reduction": baseline_cer - proposed_cer,
        "change_precision": (
            sum(row["outcome"] == "improved" for row in changed) / len(changed)
            if changed
            else 0.0
        ),
        "error_correction_recall": (
            sum(row["outcome"] == "improved" for row in erroneous) / len(erroneous)
            if erroneous
            else 0.0
        ),
        "over_correction_rate": (
            sum(row["proposed_word_errors"] > 0 for row in originally_correct)
            / len(originally_correct)
            if originally_correct
            else 0.0
        ),
        "outcomes": dict(counts),
    }


def build_transcript_rows(
    manifest_rows: Iterable[dict],
    raw_by_id: dict[int, dict],
    corrected_by_id: dict[int, dict],
    *,
    split: str | None = "test",
) -> list[dict]:
    output = []
    for manifest in manifest_rows:
        audio_id = int(manifest["audio_id"])
        if (
            (split is not None and manifest["split"] != split)
            or audio_id not in raw_by_id
            or audio_id not in corrected_by_id
        ):
            continue
        reference = manifest["reference_transcript"]
        raw = raw_by_id[audio_id]["raw_transcript"]
        corrected = corrected_by_id[audio_id]["corrected_transcript"]
        baseline = transcript_errors(reference, raw)
        proposed = transcript_errors(reference, corrected)
        if proposed["word_errors"] < baseline["word_errors"]:
            outcome = "improved"
        elif proposed["word_errors"] > baseline["word_errors"]:
            outcome = "degraded"
        else:
            outcome = "unchanged"
        output.append(
            {
                "audio_id": audio_id,
                "reference_transcript": reference,
                "raw_transcript": raw,
                "corrected_transcript": corrected,
                "baseline_word_errors": baseline["word_errors"],
                "proposed_word_errors": proposed["word_errors"],
                "reference_words": baseline["reference_words"],
                "baseline_wer": baseline["wer"],
                "proposed_wer": proposed["wer"],
                "baseline_char_errors": baseline["char_errors"],
                "proposed_char_errors": proposed["char_errors"],
                "reference_chars": baseline["reference_chars"],
                "baseline_cer": baseline["cer"],
                "proposed_cer": proposed["cer"],
                "changed": normalize_text(raw) != normalize_text(corrected),
                "outcome": outcome,
            }
        )
    return output


def page_key(item: dict) -> tuple[str, int]:
    source = item.get("source") or item.get("file_name") or ""
    return str(source), int(item.get("page") or 0)


def proxy_retrieval_metrics(retrieval: dict, k: int = 5) -> dict:
    reference = set(
        page_key(item) for item in retrieval["reference"]["final_pages"][:k]
    )
    output = {}
    for branch in ("baseline", "proposed"):
        pages = set(page_key(item) for item in retrieval[branch]["final_pages"][:k])
        union = reference | pages
        output[branch] = {
            "jaccard_at_5": len(reference & pages) / len(union) if union else 1.0,
            "overlap_recall_at_5": (
                len(reference & pages) / len(reference) if reference else 1.0
            ),
        }
    return output


def true_retrieval_metrics(
    final_pages: list[dict], gold_pairs: set[tuple[str, int]], max_rank: int = 10
) -> dict:
    ranked = [page_key(item) for item in final_pages[:max_rank]]
    relevant_ranks = [index for index, item in enumerate(ranked, start=1) if item in gold_pairs]
    metrics = {
        "hit_at_1": any(rank <= 1 for rank in relevant_ranks),
        "hit_at_3": any(rank <= 3 for rank in relevant_ranks),
        "hit_at_5": any(rank <= 5 for rank in relevant_ranks),
        "mrr_at_10": 1 / min(relevant_ranks) if relevant_ranks else 0.0,
        "recall_at_5": (
            sum(item in gold_pairs for item in ranked[:5]) / len(gold_pairs)
            if gold_pairs
            else 0.0
        ),
    }
    ideal = sum(1 / math.log2(index + 2) for index in range(min(5, len(gold_pairs))))
    actual = sum(
        (1 if item in gold_pairs else 0) / math.log2(index + 2)
        for index, item in enumerate(ranked[:5])
    )
    metrics["ndcg_at_5"] = actual / ideal if ideal else 0.0
    return metrics


def bootstrap_mean_difference(
    baseline: list[float], proposed: list[float], iterations: int = 10000, seed: int = 42
) -> dict:
    if len(baseline) != len(proposed) or not baseline:
        return {"difference": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    differences = [base - prop for base, prop in zip(baseline, proposed)]
    rng = random.Random(seed)
    samples = []
    for _ in range(iterations):
        samples.append(
            sum(rng.choice(differences) for _ in differences) / len(differences)
        )
    samples.sort()
    low = samples[int(iterations * 0.025)]
    high = samples[min(iterations - 1, int(iterations * 0.975))]
    return {
        "difference": sum(differences) / len(differences),
        "ci_low": low,
        "ci_high": high,
    }

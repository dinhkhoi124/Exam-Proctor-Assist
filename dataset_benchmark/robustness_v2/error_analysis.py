"""Unicode-safe error alignment and oracle recoverability calculations."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence
import unicodedata

from dataset_benchmark.scripts.common import sha256_file
from dataset_benchmark.scripts.metrics import normalize_text, transcript_errors


ERROR_TAXONOMY = (
    "substitution_general",
    "deletion",
    "insertion",
    "proper_noun",
    "domain_entity",
    "english_vietnamese_code_switch",
    "acronym",
    "number",
    "ip_address",
    "software_version",
    "homophone",
    "word_boundary",
    "punctuation",
    "capitalization",
    "abbreviation",
    "translation_or_semantic_rewrite",
    "other",
)

RECOVERABILITY_LEVELS = (
    "high",
    "medium",
    "low",
    "impossible_without_audio",
)


def file_provenance(path: str | Path) -> dict:
    """Return immutable identity metadata for one file read by a v2 stage."""

    target = Path(path).resolve()
    stat = target.stat()
    return {
        "path": str(target),
        "sha256": sha256_file(target),
        "size_bytes": stat.st_size,
    }


def build_stage_metadata(
    stage: str,
    *,
    inputs: Mapping[str, str | Path],
    outputs: Mapping[str, str | Path] | None = None,
    status: str = "success",
    details: Mapping[str, object] | None = None,
) -> dict:
    """Build auditable file-level provenance for a Priority 1+ stage.

    Callers must list every file they read. Outputs are hashed only after they
    exist, so a metadata record never substitutes a planned hash for a real one.
    """

    output_paths = outputs or {}
    missing_outputs = [
        name for name, path in output_paths.items() if not Path(path).exists()
    ]
    return {
        "schema_version": "1.0.0",
        "stage": stage,
        "status": status,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            name: file_provenance(path) for name, path in sorted(inputs.items())
        },
        "outputs": {
            name: file_provenance(path)
            for name, path in sorted(output_paths.items())
            if Path(path).exists()
        },
        "missing_outputs": missing_outputs,
        "details": dict(details or {}),
    }


@dataclass(frozen=True)
class ErrorSpan:
    """A contiguous word-level edit with half-open token offsets."""

    error_id: str
    type: str
    reference_span: str
    hypothesis_span: str
    reference_start: int
    reference_end: int
    hypothesis_start: int
    hypothesis_end: int
    edit_count: int
    wer_edit_count: int

    def to_dict(self) -> dict:
        return asdict(self)


def _word_tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", text or "")
    return re.findall(r"\w+|[^\w\s]", normalized, flags=re.UNICODE)


def _alignment_steps(
    reference_tokens: Sequence[str], hypothesis_tokens: Sequence[str]
) -> list[tuple[str, int, int, int, int]]:
    """Return deterministic minimal-edit alignment steps.

    Ties prefer substitution, then deletion, then insertion. This makes repeated
    token alignments reproducible across runs and Python versions.
    """

    ref_count, hyp_count = len(reference_tokens), len(hypothesis_tokens)
    costs = [[0] * (hyp_count + 1) for _ in range(ref_count + 1)]
    choices: list[list[str | None]] = [
        [None] * (hyp_count + 1) for _ in range(ref_count + 1)
    ]
    for ref_index in range(1, ref_count + 1):
        costs[ref_index][0] = ref_index
        choices[ref_index][0] = "deletion"
    for hyp_index in range(1, hyp_count + 1):
        costs[0][hyp_index] = hyp_index
        choices[0][hyp_index] = "insertion"

    priority = {"substitution": 0, "deletion": 1, "insertion": 2}
    for ref_index in range(1, ref_count + 1):
        for hyp_index in range(1, hyp_count + 1):
            if reference_tokens[ref_index - 1] == hypothesis_tokens[hyp_index - 1]:
                costs[ref_index][hyp_index] = costs[ref_index - 1][hyp_index - 1]
                choices[ref_index][hyp_index] = "correct"
                continue
            candidates = (
                (costs[ref_index - 1][hyp_index - 1] + 1, "substitution"),
                (costs[ref_index - 1][hyp_index] + 1, "deletion"),
                (costs[ref_index][hyp_index - 1] + 1, "insertion"),
            )
            cost, operation = min(
                candidates, key=lambda item: (item[0], priority[item[1]])
            )
            costs[ref_index][hyp_index] = cost
            choices[ref_index][hyp_index] = operation

    steps = []
    ref_index, hyp_index = ref_count, hyp_count
    while ref_index > 0 or hyp_index > 0:
        operation = choices[ref_index][hyp_index]
        if operation in {"correct", "substitution"}:
            steps.append(
                (operation, ref_index - 1, ref_index, hyp_index - 1, hyp_index)
            )
            ref_index -= 1
            hyp_index -= 1
        elif operation == "deletion":
            steps.append((operation, ref_index - 1, ref_index, hyp_index, hyp_index))
            ref_index -= 1
        elif operation == "insertion":
            steps.append((operation, ref_index, ref_index, hyp_index - 1, hyp_index))
            hyp_index -= 1
        else:
            raise RuntimeError("Alignment backtrace reached an invalid state")
    steps.reverse()
    return steps


def align_error_spans(sample_id: str | int, reference: str, hypothesis: str) -> list[ErrorSpan]:
    """Align two transcripts and return structured non-correct error spans."""

    reference_tokens = _word_tokens(reference)
    hypothesis_tokens = _word_tokens(hypothesis)
    steps = _alignment_steps(reference_tokens, hypothesis_tokens)
    groups: list[list[tuple[str, int, int, int, int]]] = []
    for step in steps:
        if step[0] == "correct":
            continue
        if (
            groups
            and groups[-1][-1][0] == step[0]
            and groups[-1][-1][2] == step[1]
            and groups[-1][-1][4] == step[3]
        ):
            groups[-1].append(step)
        else:
            groups.append([step])

    errors = []
    for error_index, group in enumerate(groups, start=1):
        operation = group[0][0]
        ref_start, ref_end = group[0][1], group[-1][2]
        hyp_start, hyp_end = group[0][3], group[-1][4]
        errors.append(
            ErrorSpan(
                error_id=f"{sample_id}_e{error_index:03d}",
                type=operation,
                reference_span=" ".join(reference_tokens[ref_start:ref_end]),
                hypothesis_span=" ".join(hypothesis_tokens[hyp_start:hyp_end]),
                reference_start=ref_start,
                reference_end=ref_end,
                hypothesis_start=hyp_start,
                hypothesis_end=hyp_end,
                edit_count=len(group),
                wer_edit_count=transcript_errors(
                    " ".join(reference_tokens[ref_start:ref_end]),
                    " ".join(hypothesis_tokens[hyp_start:hyp_end]),
                )["word_errors"],
            )
        )
    return errors


def align_transcripts(
    sample_id: str | int, reference: str, raw_transcript: str, corrected_transcript: str
) -> dict:
    """Return raw and corrected alignments for one benchmark sample."""

    return {
        "sample_id": sample_id,
        "reference": reference,
        "raw_transcript": raw_transcript,
        "corrected_transcript": corrected_transcript,
        "raw_errors": [
            error.to_dict()
            for error in align_error_spans(sample_id, reference, raw_transcript)
        ],
        "corrected_errors": [
            error.to_dict()
            for error in align_error_spans(sample_id, reference, corrected_transcript)
        ],
    }


def _same_error(first: ErrorSpan, second: ErrorSpan) -> bool:
    return (
        first.type,
        first.reference_start,
        first.reference_end,
        first.reference_span,
        first.hypothesis_span,
    ) == (
        second.type,
        second.reference_start,
        second.reference_end,
        second.reference_span,
        second.hypothesis_span,
    )


def _overlaps_reference(first: ErrorSpan, second: ErrorSpan) -> bool:
    if first.reference_start == first.reference_end:
        return (
            second.type == "insertion"
            and second.reference_start == first.reference_start
        )
    if second.reference_start == second.reference_end:
        return first.reference_start <= second.reference_start <= first.reference_end
    return max(first.reference_start, second.reference_start) < min(
        first.reference_end, second.reference_end
    )


def build_annotation_records(
    manifest_rows: Iterable[dict],
    raw_by_id: dict[int, dict],
    corrected_by_id: dict[int, dict],
) -> list[dict]:
    """Build raw-error and correction-introduced records for human annotation."""

    records = []
    for manifest in manifest_rows:
        if manifest.get("eligibility_status") != "eligible":
            continue
        sample_id = int(manifest["audio_id"])
        if sample_id not in raw_by_id or sample_id not in corrected_by_id:
            continue
        reference = manifest["reference_transcript"]
        raw = raw_by_id[sample_id].get("raw_transcript", "")
        corrected = corrected_by_id[sample_id].get("corrected_transcript", raw)
        raw_errors = align_error_spans(sample_id, reference, raw)
        corrected_errors = align_error_spans(sample_id, reference, corrected)
        raw_metrics = transcript_errors(reference, raw)
        corrected_metrics = transcript_errors(reference, corrected)
        common = {
            "sample_id": sample_id,
            "speaker": manifest.get("speaker", ""),
            "intent": manifest.get("intent", ""),
            "reference": reference,
            "raw_transcript": raw,
            "corrected_transcript": corrected,
            "reference_word_count": raw_metrics["reference_words"],
            "raw_word_errors": raw_metrics["word_errors"],
            "corrected_word_errors": corrected_metrics["word_errors"],
            "raw_wer": raw_metrics["wer"],
            "corrected_wer": corrected_metrics["wer"],
            "transcript_changed": unicodedata.normalize(
                "NFC", raw.strip()
            ) != unicodedata.normalize("NFC", corrected.strip()),
        }
        for error in raw_errors:
            unresolved = any(
                _overlaps_reference(error, corrected_error)
                for corrected_error in corrected_errors
            )
            records.append(
                {
                    **common,
                    "error_source": "raw_asr",
                    **error.to_dict(),
                    "correction_resolved": not unresolved,
                }
            )
        introduced_index = 0
        for error in corrected_errors:
            if any(_same_error(error, raw_error) for raw_error in raw_errors):
                continue
            introduced_index += 1
            source = (
                "correction_residual"
                if any(
                    _overlaps_reference(raw_error, error)
                    for raw_error in raw_errors
                )
                else "correction_introduced"
            )
            payload = error.to_dict()
            payload["error_id"] = f"{sample_id}_c{introduced_index:03d}"
            records.append(
                {
                    **common,
                    "error_source": source,
                    **payload,
                    "correction_resolved": False,
                }
            )
    return records


def wer_bin(value: float) -> str:
    """Return the fixed WER bin required by the benchmark specification."""

    if value == 0:
        return "WER = 0"
    if value <= 0.05:
        return "0 < WER <= 5%"
    if value <= 0.15:
        return "5% < WER <= 15%"
    if value <= 0.30:
        return "15% < WER <= 30%"
    return "WER > 30%"


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def cohen_kappa(first: Sequence[str], second: Sequence[str]) -> float:
    """Calculate unweighted Cohen's kappa without an external dependency."""

    if len(first) != len(second) or not first:
        raise ValueError("Kappa requires two non-empty label sequences of equal length")
    labels = sorted(set(first) | set(second))
    observed = sum(a == b for a, b in zip(first, second)) / len(first)
    first_counts, second_counts = Counter(first), Counter(second)
    expected = sum(
        first_counts[label] * second_counts[label] for label in labels
    ) / (len(first) ** 2)
    return 1.0 if expected == 1.0 and observed == 1.0 else _safe_ratio(
        observed - expected, 1.0 - expected
    )


def weighted_cohen_kappa(
    first: Sequence[str], second: Sequence[str], ordered_labels: Sequence[str]
) -> float:
    """Calculate quadratic-weighted Cohen's kappa."""

    if len(first) != len(second) or not first:
        raise ValueError("Kappa requires two non-empty label sequences of equal length")
    positions = {label: index for index, label in enumerate(ordered_labels)}
    if any(label not in positions for label in list(first) + list(second)):
        raise ValueError("Unknown label supplied to weighted kappa")
    scale = max(1, len(ordered_labels) - 1)
    observed_disagreement = sum(
        ((positions[a] - positions[b]) / scale) ** 2
        for a, b in zip(first, second)
    ) / len(first)
    first_counts, second_counts = Counter(first), Counter(second)
    expected_disagreement = sum(
        first_counts[a]
        * second_counts[b]
        * (((positions[a] - positions[b]) / scale) ** 2)
        for a in ordered_labels
        for b in ordered_labels
    ) / (len(first) ** 2)
    return 1.0 if expected_disagreement == 0 else 1.0 - (
        observed_disagreement / expected_disagreement
    )


def confusion_matrix(
    first: Sequence[str], second: Sequence[str], labels: Sequence[str]
) -> dict[str, dict[str, int]]:
    matrix = {row: {column: 0 for column in labels} for row in labels}
    for first_label, second_label in zip(first, second):
        matrix[first_label][second_label] += 1
    return matrix


def inter_rater_metrics(first_rows: Sequence[dict], second_rows: Sequence[dict]) -> dict:
    """Calculate agreement metrics after matching rows by stable error ID."""

    first = {row["error_id"]: row for row in first_rows}
    second = {row["error_id"]: row for row in second_rows}
    if set(first) != set(second) or not first:
        raise ValueError("Rater workbooks must contain the same non-empty error IDs")
    ids = sorted(first)
    taxonomy_a = [first[error_id]["primary_taxonomy"] for error_id in ids]
    taxonomy_b = [second[error_id]["primary_taxonomy"] for error_id in ids]
    recoverability_a = [first[error_id]["text_recoverability"] for error_id in ids]
    recoverability_b = [second[error_id]["text_recoverability"] for error_id in ids]
    return {
        "items": len(ids),
        "taxonomy": {
            "cohen_kappa": cohen_kappa(taxonomy_a, taxonomy_b),
            "raw_agreement": _safe_ratio(
                sum(a == b for a, b in zip(taxonomy_a, taxonomy_b)), len(ids)
            ),
            "confusion_matrix": confusion_matrix(
                taxonomy_a, taxonomy_b, ERROR_TAXONOMY
            ),
        },
        "recoverability": {
            "weighted_cohen_kappa": weighted_cohen_kappa(
                recoverability_a, recoverability_b, RECOVERABILITY_LEVELS
            ),
            "raw_agreement": _safe_ratio(
                sum(a == b for a, b in zip(recoverability_a, recoverability_b)),
                len(ids),
            ),
            "confusion_matrix": confusion_matrix(
                recoverability_a, recoverability_b, RECOVERABILITY_LEVELS
            ),
        },
    }


def oracle_metrics(
    rows: Sequence[dict], *, total_reference_words: int | None = None
) -> dict:
    """Calculate oracle bounds and correction behavior from final annotations."""

    if not rows:
        raise ValueError("Oracle evaluation requires at least one annotated error")
    raw_rows = [row for row in rows if row["error_source"] == "raw_asr"]
    introduced_rows = [
        row for row in rows if row["error_source"] == "correction_introduced"
    ]
    sample_rows: dict[int, dict] = {}
    for row in rows:
        sample_rows[int(row["sample_id"])] = row
    reference_words = total_reference_words or sum(
        int(row["reference_word_count"]) for row in sample_rows.values()
    )
    high_edits = sum(
        int(row["wer_edit_count"])
        for row in raw_rows
        if row["text_recoverability"] == "high"
    )
    recoverable = [
        row
        for row in raw_rows
        if row["text_recoverability"] in {"high", "medium"}
    ]
    recoverable_edits = sum(int(row["wer_edit_count"]) for row in recoverable)
    resolved_edits = sum(
        int(row["wer_edit_count"])
        for row in recoverable
        if row["correction_resolved"]
    )
    changed_samples = [row for row in sample_rows.values() if row["transcript_changed"]]
    improved_samples = [
        row
        for row in changed_samples
        if int(row["corrected_word_errors"]) < int(row["raw_word_errors"])
    ]

    def subgroup(field: str) -> dict:
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in raw_rows:
            value = row.get(field) or "unknown"
            grouped[str(value)].append(row)
        output = {}
        for value, group in sorted(grouped.items()):
            group_recoverable = [
                row
                for row in group
                if row["text_recoverability"] in {"high", "medium"}
            ]
            output[value] = {
                "error_spans": len(group),
                "recoverable_error_spans": len(group_recoverable),
                "correction_recall": _safe_ratio(
                    sum(bool(row["correction_resolved"]) for row in group_recoverable),
                    len(group_recoverable),
                ),
            }
        return output

    taxonomy_counts = Counter(row["primary_taxonomy"] for row in raw_rows)
    recoverability_counts = Counter(row["text_recoverability"] for row in raw_rows)
    overcorrection_counts = Counter(
        row["primary_taxonomy"] for row in introduced_rows
    )
    return {
        "total_error_spans": len(raw_rows),
        "total_error_edits": sum(int(row["edit_count"]) for row in raw_rows),
        "total_wer_error_edits": sum(
            int(row["wer_edit_count"]) for row in raw_rows
        ),
        "total_reference_words": reference_words,
        "taxonomy": {
            label: {
                "count": taxonomy_counts[label],
                "rate": _safe_ratio(taxonomy_counts[label], len(raw_rows)),
            }
            for label in ERROR_TAXONOMY
        },
        "recoverability": {
            label: {
                "count": recoverability_counts[label],
                "rate": _safe_ratio(recoverability_counts[label], len(raw_rows)),
            }
            for label in RECOVERABILITY_LEVELS
        },
        "high_recoverable_edits": high_edits,
        "high_medium_recoverable_edits": recoverable_edits,
        "maximum_recoverable_wer_reduction_high": _safe_ratio(
            high_edits, reference_words
        ),
        "maximum_recoverable_wer_reduction_high_medium": _safe_ratio(
            recoverable_edits, reference_words
        ),
        "correction_recall_on_recoverable_errors": _safe_ratio(
            resolved_edits, recoverable_edits
        ),
        "correction_precision_on_changed_samples": _safe_ratio(
            len(improved_samples), len(changed_samples)
        ),
        "changed_samples": len(changed_samples),
        "improved_changed_samples": len(improved_samples),
        "overcorrection": {
            "introduced_error_spans": len(introduced_rows),
            "by_taxonomy": dict(sorted(overcorrection_counts.items())),
        },
        "by_speaker": subgroup("speaker"),
        "by_intent": subgroup("intent"),
        "by_raw_wer_bin": subgroup("raw_wer_bin"),
    }

import hashlib

from dataset_benchmark.robustness_v2.error_analysis import (
    RECOVERABILITY_LEVELS,
    align_error_spans,
    build_stage_metadata,
    cohen_kappa,
    oracle_metrics,
    weighted_cohen_kappa,
)


def test_stage_metadata_hashes_every_named_input_and_existing_output(tmp_path):
    manifest = tmp_path / "manifest.csv"
    transcript = tmp_path / "raw.jsonl"
    output = tmp_path / "annotations.xlsx"
    manifest.write_bytes("audio_id,reference_transcript\n1,xin chào\n".encode("utf-8"))
    transcript.write_text('{"audio_id": 1}\n', encoding="utf-8")
    output.write_bytes(b"workbook-fixture")

    metadata = build_stage_metadata(
        "test_stage",
        inputs={"manifest": manifest, "raw_transcripts": transcript},
        outputs={"workbook": output},
    )

    assert set(metadata["inputs"]) == {"manifest", "raw_transcripts"}
    assert metadata["inputs"]["manifest"]["sha256"] == hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest()
    assert metadata["outputs"]["workbook"]["sha256"] == hashlib.sha256(
        output.read_bytes()
    ).hexdigest()
    assert metadata["missing_outputs"] == []


def test_alignment_substitution_unicode_vietnamese():
    errors = align_error_spans(141, "Làm sao cấu hình IP tĩnh", "Làm sao cấu hình IP tỉnh")
    assert [error.type for error in errors] == ["substitution"]
    assert errors[0].reference_span == "tĩnh"
    assert errors[0].hypothesis_span == "tỉnh"
    assert errors[0].reference_start == 5
    assert errors[0].reference_end == 6


def test_alignment_deletion_insertion_and_empty_transcript():
    deletion = align_error_spans("x", "một hai ba", "một ba")
    insertion = align_error_spans("x", "một ba", "một hai ba")
    empty = align_error_spans("x", "một hai", "")
    assert [(item.type, item.reference_span) for item in deletion] == [
        ("deletion", "hai")
    ]
    assert [(item.type, item.hypothesis_span) for item in insertion] == [
        ("insertion", "hai")
    ]
    assert empty[0].type == "deletion"
    assert empty[0].edit_count == 2


def test_alignment_repeated_tokens_is_deterministic():
    first = align_error_spans("r", "wifi wifi student", "wifi student")
    second = align_error_spans("r", "wifi wifi student", "wifi student")
    assert first == second
    assert sum(error.edit_count for error in first) == 1


def test_alignment_exposes_punctuation_and_capitalization_without_counting_wer():
    punctuation = align_error_spans("p", "Nội quy!", "Nội quy")
    capitalization = align_error_spans("c", "WiFi Student", "wifi Student")
    assert punctuation[0].type == "deletion"
    assert punctuation[0].wer_edit_count == 0
    assert capitalization[0].type == "substitution"
    assert capitalization[0].wer_edit_count == 0


def test_kappa_metrics_without_sklearn():
    labels = ["a", "b", "a", "b"]
    assert cohen_kappa(labels, labels) == 1.0
    recoverability = list(RECOVERABILITY_LEVELS)
    assert weighted_cohen_kappa(
        recoverability, recoverability, RECOVERABILITY_LEVELS
    ) == 1.0


def test_oracle_metrics_use_edit_counts_and_base_samples():
    common = {
        "sample_id": 1,
        "error_source": "raw_asr",
        "edit_count": 1,
        "wer_edit_count": 1,
        "reference_word_count": 4,
        "raw_word_errors": 1,
        "corrected_word_errors": 0,
        "transcript_changed": True,
        "correction_resolved": True,
        "primary_taxonomy": "homophone",
        "text_recoverability": "high",
        "speaker": "A",
        "intent": "network",
        "raw_wer_bin": "15% < WER <= 30%",
    }
    metrics = oracle_metrics([common])
    assert metrics["maximum_recoverable_wer_reduction_high"] == 0.25
    assert metrics["correction_recall_on_recoverable_errors"] == 1.0
    assert metrics["correction_precision_on_changed_samples"] == 1.0

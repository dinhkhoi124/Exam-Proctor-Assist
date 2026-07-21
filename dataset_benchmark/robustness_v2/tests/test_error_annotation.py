from copy import deepcopy

import pytest

from dataset_benchmark.robustness_v2.error_analysis import build_annotation_records
from dataset_benchmark.robustness_v2.scripts.evaluate_oracle_recoverability import (
    final_annotations,
    validate_rater_rows,
)
from dataset_benchmark.robustness_v2.scripts.prepare_error_analysis_annotation import (
    create_rater_workbooks,
)


def _record():
    return {
        "sample_id": 1,
        "speaker": "A",
        "intent": "",
        "reference": "nội quy",
        "raw_transcript": "nội huy",
        "corrected_transcript": "nội quy",
        "error_id": "1_e001",
        "error_source": "raw_asr",
        "type": "substitution",
        "reference_span": "quy",
        "hypothesis_span": "huy",
        "reference_start": 1,
        "reference_end": 2,
        "hypothesis_start": 1,
        "hypothesis_end": 2,
        "edit_count": 1,
        "wer_edit_count": 1,
        "correction_resolved": True,
        "reference_word_count": 2,
        "raw_word_errors": 1,
        "corrected_word_errors": 0,
        "raw_wer": 0.5,
        "corrected_wer": 0.0,
        "transcript_changed": True,
    }


def test_workbooks_are_reproducible_and_separate(tmp_path):
    targets = create_rater_workbooks([_record()], tmp_path, seed=7)
    assert [target.name for target in targets] == [
        "error_analysis_rater_A.xlsx",
        "error_analysis_rater_B.xlsx",
    ]
    assert all(target.exists() for target in targets)


def test_blank_workbook_row_is_not_valid_annotation():
    row = {
        "error_id": "1_e001",
        "primary_taxonomy": "",
        "text_recoverability": "",
        "annotator": "",
        "reviewed_status": "",
    }
    with pytest.raises(ValueError, match="blank or invalid"):
        validate_rater_rows([row], "rater A")


def test_invalid_secondary_taxonomy_is_rejected():
    row = {
        "error_id": "1_e001",
        "primary_taxonomy": "homophone",
        "secondary_tags": "not_a_taxonomy",
        "text_recoverability": "high",
        "annotator": "rater",
        "reviewed_status": "reviewed",
    }
    with pytest.raises(ValueError, match="secondary_tags contains invalid"):
        validate_rater_rows([row], "rater A")


def test_disagreement_requires_adjudication():
    first = {
        **_record(),
        "primary_taxonomy": "homophone",
        "text_recoverability": "high",
    }
    second = deepcopy(first)
    second["primary_taxonomy"] = "substitution_general"
    with pytest.raises(ValueError, match="unresolved rater disagreement"):
        final_annotations([first], [second], None)


def test_annotation_records_include_overcorrection_errors():
    manifest = [
        {
            "audio_id": "1",
            "speaker": "A",
            "reference_transcript": "email",
            "eligibility_status": "eligible",
        }
    ]
    raw = {1: {"raw_transcript": "email"}}
    corrected = {1: {"corrected_transcript": "gmail"}}
    rows = build_annotation_records(manifest, raw, corrected)
    assert [row["error_source"] for row in rows] == ["correction_introduced"]
    assert rows[0]["error_id"] == "1_c001"

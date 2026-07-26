from app.rag.evidence_selector import select_primary_evidence_source


def test_primary_source_uses_total_retrieval_score():
    evidence_by_id = {
        "E1": {"file_name": "secondary.pdf", "score": 0.01},
        "E2": {"file_name": "primary.pdf", "score": 0.03},
        "E3": {"file_name": "primary.pdf", "score": 0.02},
    }

    selected = select_primary_evidence_source(
        ["E1", "E2", "E3"],
        evidence_by_id,
    )

    assert selected == "primary.pdf"


def test_primary_source_falls_back_to_evidence_count_then_order():
    evidence_by_id = {
        "E1": {"file_name": "first.pdf"},
        "E2": {"file_name": "second.pdf"},
        "E3": {"file_name": "second.pdf"},
    }

    selected = select_primary_evidence_source(
        ["E1", "E2", "E3", "E2"],
        evidence_by_id,
    )

    assert selected == "second.pdf"


def test_primary_source_returns_none_without_valid_citations():
    assert select_primary_evidence_source(["E9"], {}) is None

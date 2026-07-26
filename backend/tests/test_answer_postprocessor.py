from app.services.answer_postprocessor import (
    extract_evidence_ids,
    normalize_evidence_citations,
    strip_evidence_citations,
)


def test_normalize_common_evidence_variants():
    answer = "Mật khẩu là Fu-Exam@. [Sử dụng E1] Nguồn khác. [Nguồn: E2]"

    assert normalize_evidence_citations(answer) == (
        "Mật khẩu là Fu-Exam@. [E1] Nguồn khác. [E2]"
    )


def test_extract_evidence_ids_preserves_order():
    answer = "Bước một. [E2] Bước hai. [Evidence E1]"

    assert extract_evidence_ids(answer) == ["E2", "E1"]


def test_strip_evidence_citations_cleans_display_text():
    answer = "Bạn thực hiện như sau: [Sử dụng E1]\n\n1. Chọn Wi-Fi [E1]."

    assert strip_evidence_citations(answer) == (
        "Bạn thực hiện như sau:\n\n1. Chọn Wi-Fi."
    )

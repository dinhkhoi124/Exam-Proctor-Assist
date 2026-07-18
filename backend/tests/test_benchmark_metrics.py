from dataset_benchmark.scripts.metrics import (
    build_transcript_rows,
    normalize_text,
    proxy_retrieval_metrics,
    transcript_errors,
    true_retrieval_metrics,
)


def test_transcript_rows_can_evaluate_an_explicit_dev_subset():
    manifest = [
        {
            "audio_id": "5",
            "split": "dev",
            "reference_transcript": "nội quy",
        }
    ]
    raw = {5: {"raw_transcript": "nội huy"}}
    corrected = {5: {"corrected_transcript": "nội quy"}}

    assert build_transcript_rows(manifest, raw, corrected) == []
    rows = build_transcript_rows(manifest, raw, corrected, split=None)
    assert len(rows) == 1
    assert rows[0]["outcome"] == "improved"


def test_normalization_and_wer_are_deterministic():
    assert normalize_text("  Nội QUY, kỳ thi! ") == "nội quy kỳ thi"
    metrics = transcript_errors("nội quy kỳ thi", "nội huy kỳ thi")
    assert metrics["word_errors"] == 1
    assert metrics["reference_words"] == 4


def test_proxy_retrieval_overlap():
    result = {
        "reference": {"final_pages": [{"source": "a.pdf", "page": 1}]},
        "baseline": {"final_pages": [{"source": "b.pdf", "page": 1}]},
        "proposed": {"final_pages": [{"source": "a.pdf", "page": 1}]},
    }
    metrics = proxy_retrieval_metrics(result)
    assert metrics["baseline"]["jaccard_at_5"] == 0
    assert metrics["proposed"]["jaccard_at_5"] == 1


def test_true_retrieval_metrics():
    pages = [
        {"source": "wrong.pdf", "page": 1},
        {"source": "gold.pdf", "page": 3},
    ]
    metrics = true_retrieval_metrics(pages, {("gold.pdf", 3)})
    assert metrics["hit_at_1"] is False
    assert metrics["hit_at_3"] is True
    assert metrics["mrr_at_10"] == 0.5

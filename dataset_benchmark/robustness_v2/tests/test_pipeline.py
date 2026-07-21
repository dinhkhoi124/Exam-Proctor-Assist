from dataset_benchmark.robustness_v2.pipeline import (
    HeuristicCorrectionRiskDetector,
    RiskDetectorInput,
    correction_cache_key,
    correction_requirements,
    risk_cache_key,
    select_pipeline_transcript,
    stt_cache_key,
    tune_thresholds,
)


def _detector_config(threshold=0.6):
    return {
        "version": "heuristic_v1",
        "threshold": threshold,
        "minimum_tokens": 3,
        "retrieval_top1_min": 0.2,
        "retrieval_margin_min": 0.1,
        "weights": {
            "empty_transcript": 1.0,
            "short_transcript": 0.35,
            "low_retrieval_score": 0.4,
            "ambiguous_top1_top2_margin": 0.3,
        },
    }


def test_detector_is_deterministic_and_explains_high_risk():
    detector = HeuristicCorrectionRiskDetector(_detector_config())
    sample = RiskDetectorInput(raw_transcript="", retrieval_metadata={"candidates": []})
    first = detector.score(sample)
    second = detector.score(sample)
    assert first == second
    assert first.decision == "correct"
    assert "empty_transcript" in first.reasons
    assert first.detector_version == "heuristic_v1"


def test_p0_never_requests_correction_and_p1_requests_once():
    assert correction_requirements(("P0",), "correct") == ()
    assert correction_requirements(("P1",), "use_raw") == ("P1",)
    assert correction_requirements(("P0", "P1", "P2"), "correct") == (
        "P1",
        "P2",
    )


def test_p2_only_requests_correction_for_detector_correct_decision():
    assert correction_requirements(("P2",), "use_raw") == ()
    assert correction_requirements(("P2",), "correct") == ("P2",)


def test_all_pipelines_route_from_the_same_cached_raw_transcript():
    raw = "wifi student"
    correction = {"status": "success", "corrected_transcript": "WiFi Student"}
    low = {"decision": "use_raw"}
    high = {"decision": "correct"}
    assert select_pipeline_transcript(
        "P0", raw_transcript=raw, correction_record=correction, risk_record=high
    ) == (raw, "raw")
    assert select_pipeline_transcript(
        "P1", raw_transcript=raw, correction_record=correction, risk_record=low
    ) == ("WiFi Student", "corrected")
    assert select_pipeline_transcript(
        "P2", raw_transcript=raw, correction_record=correction, risk_record=low
    ) == (raw, "raw")
    assert select_pipeline_transcript(
        "P2", raw_transcript=raw, correction_record=correction, risk_record=high
    ) == ("WiFi Student", "corrected")


def test_correction_failure_falls_back_to_raw_for_retrieval():
    selected = select_pipeline_transcript(
        "P1",
        raw_transcript="raw query",
        correction_record={"status": "fallback", "corrected_transcript": "bad"},
        risk_record={"decision": "correct"},
    )
    assert selected == ("raw query", "raw_fallback")


def test_audio_hash_change_invalidates_stt_cache():
    config = {"model": "stt", "prompt": "vi"}
    assert stt_cache_key("audio-a", config) != stt_cache_key("audio-b", config)


def test_prompt_or_model_change_invalidates_correction_cache():
    base = {
        "model": "gpt-4o-mini",
        "temperature": 0,
        "service_version": "v1",
        "prompt_sha256": "prompt-a",
    }
    prompt_changed = {**base, "prompt_sha256": "prompt-b"}
    model_changed = {**base, "model": "other"}
    assert correction_cache_key("raw", base) != correction_cache_key(
        "raw", prompt_changed
    )
    assert correction_cache_key("raw", base) != correction_cache_key(
        "raw", model_changed
    )


def test_detector_or_retrieval_config_change_invalidates_risk_cache():
    detector = {"version": "v1", "threshold": 0.6}
    retrieval = {"top_k": 15}
    first = risk_cache_key("raw", detector, retrieval)
    assert first != risk_cache_key("raw", {**detector, "threshold": 0.7}, retrieval)
    assert first != risk_cache_key("raw", detector, {"top_k": 5})


def test_threshold_tuning_penalizes_calls_and_overcorrection():
    rows = [
        {
            "risk_score": 0.8,
            "reference_transcript": "mật khẩu",
            "raw_transcript": "mật khâu",
            "corrected_transcript": "mật khẩu",
        },
        {
            "risk_score": 0.4,
            "reference_transcript": "wifi",
            "raw_transcript": "wifi",
            "corrected_transcript": "wife",
        },
    ]
    result = tune_thresholds(
        rows, [0.3, 0.6], lambda_cost=0.01, lambda_overcorrection=0.5
    )
    assert result[0]["threshold"] == 0.6
    assert result[0]["correction_call_rate"] == 0.5

import json
import wave

from dataset_benchmark.robustness_v2.evaluation import (
    aggregate_retrieval_pipeline,
    aggregate_transcript_pipeline,
    base_aggregates,
    cluster_bootstrap,
    holm_adjust,
    paired_wilcoxon,
    two_way_cluster_bootstrap,
)
from dataset_benchmark.robustness_v2.scripts.evaluate_robustness import (
    actual_cost_accounting,
    paired_noise_source_sensitivity,
    primary_evidence_rows,
)
from dataset_benchmark.robustness_v2.scripts.generate_robustness_report import generate
from dataset_benchmark.scripts.common import resolve_path


def _sample(base_id, pipeline, wer, proxy=1.0):
    return {
        "base_id": base_id,
        "pipeline": pipeline,
        "word_errors": int(wer > 0),
        "reference_words": 2,
        "char_errors": int(wer > 0),
        "reference_chars": 4,
        "wer": wer,
        "cer": wer,
        "raw_word_errors": 1,
        "outcome_vs_p0": "improved" if wer == 0 else "unchanged",
        "transcript_changed_vs_p0": pipeline != "P0",
        "hallucinated_token_rate_proxy": 0.0,
        "semantic_rewrite_proxy": 0.0,
        "retrieval_proxy_available": True,
        "jaccard_at_5_proxy": proxy,
        "overlap_recall_at_5_proxy": proxy,
        "retrieval_gold_available": False,
    }


def test_base_aggregates_do_not_treat_variants_as_independent():
    rows = [
        _sample(1, "P0", 0.5),
        _sample(1, "P0", 0.0),
        _sample(1, "P1", 0.0),
        _sample(1, "P1", 0.0),
    ]
    result = base_aggregates(rows)
    assert len(result) == 2
    p0 = next(row for row in result if row["pipeline"] == "P0")
    assert p0["variants"] == 2
    assert p0["mean_wer"] == 0.25


def test_cluster_bootstrap_reports_base_unit_and_paired_difference():
    result = cluster_bootstrap([0.5, 0.0], [0.0, 0.0], iterations=100, seed=7)
    assert result["unit"] == "base_id"
    assert result["independent_base_utterances"] == 2
    assert result["candidate_minus_p0"] == -0.25


def test_paired_wilcoxon_handles_all_zero_differences():
    result = paired_wilcoxon([0.0, 0.5], [0.0, 0.5])
    assert result["p_value"] == 1.0
    assert result["all_differences_zero"] is True


def test_holm_adjustment_is_monotonic_and_keeps_missing_values():
    result = holm_adjust({"a": 0.01, "b": 0.04, "missing": None})
    assert result["a"] == 0.02
    assert result["b"] == 0.04
    assert result["missing"] is None


def test_proxy_and_true_gold_metrics_are_not_mixed():
    summary = aggregate_retrieval_pipeline([_sample(1, "P0", 0.0, proxy=0.5)])
    assert summary["proxy"]["availability"] == "available"
    assert summary["proxy"]["jaccard_at_5"] == 0.5
    assert summary["true_gold"]["availability"] == "unavailable"


def test_transcript_aggregation_reports_independent_base_count():
    summary = aggregate_transcript_pipeline(
        [_sample(1, "P1", 0.0), _sample(1, "P1", 0.0)]
    )
    assert summary["samples"] == 2
    assert summary["independent_base_utterances"] == 1
    assert summary["improved_count"] == 2


def test_pilot_selection_order_is_explicitly_non_randomized():
    rows = [
        {"base_id": 110, "variant_id": "110_c0"},
        {"base_id": 101, "variant_id": "101_c0"},
        {"base_id": 102, "variant_id": "102_c0"},
    ]
    ordered = sorted(rows, key=lambda row: (int(row["base_id"]), row["variant_id"]))
    assert [row["base_id"] for row in ordered[:2]] == [101, 102]


def test_report_renders_full_scope_without_pilot_hard_code(tmp_path):
    source = resolve_path(
        "dataset_benchmark/robustness_v2/reports/robustness_v2_summary.json"
    )
    summary = json.loads(source.read_text(encoding="utf-8"))
    summary["dataset"].update(
        {
            "conditions": ["C0", "C1", "C2", "C3"],
            "independent_base_utterances": 130,
            "audio_variants": 1040,
            "pipeline_records": 3120,
            "speakers": 2,
            "speaker_values": ["Toàn", "Trí"],
            "evaluated_base_ids": list(range(101, 231)),
            "selection": {
                "selection": "all 130 base IDs",
                "ordering": "manifest order",
                "randomized": False,
            },
        }
    )
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    report = generate({"outputs": {"evaluation_summary": str(path)}})
    assert "full 130-base, 1,040-variant C0-C3 local run" in report
    assert "10-base C0 pilot only" not in report


def test_actual_cost_accounting_uses_observed_audio_and_route_tokens(tmp_path):
    audio = tmp_path / "sample.wav"
    with wave.open(str(audio), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * 16000 * 60)

    def write_jsonl(name, rows):
        path = tmp_path / name
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        return path

    paths = {
        "run_manifest": write_jsonl(
            "manifest.jsonl",
            [{"variant_id": "v1", "output_audio_path": str(audio)}],
        ),
        "stt_cache": write_jsonl(
            "stt.jsonl", [{"variant_id": "v1", "cache_origin": "api"}]
        ),
        "correction_cache": write_jsonl(
            "corrections.jsonl",
            [{"cache_origin": "api", "required_by": ["P1"], "prompt_tokens": 1000, "completion_tokens": 100}],
        ),
        "answer_cache": write_jsonl(
            "answers.jsonl",
            [{"cache_origin": "api", "pipeline": "P0", "prompt_tokens": 1000, "completion_tokens": 100}],
        ),
        "judge_cache": write_jsonl(
            "judge.jsonl",
            [{"cache_origin": "api", "pipeline": "P0", "prompt_tokens": 1000, "completion_tokens": 100}],
        ),
    }
    config = {
        "cost": {
            "as_of": "test",
            "models": {
                "gpt-4o-mini": {
                    "input_per_million_tokens": 0.15,
                    "output_per_million_tokens": 0.60,
                },
                "gpt-4o-mini-transcribe": {"per_minute_assumption": 0.003},
            },
        }
    }
    result = actual_cost_accounting(config, paths)
    assert result["unique_run_spend_usd"]["total"] == 0.00363
    assert result["route_comparison"]["P0"]["total_usd"] == 0.00342
    assert result["route_comparison"]["P1"]["total_usd"] == 0.00321
    assert result["route_comparison"]["P2"]["total_usd"] == 0.003


def test_primary_evidence_filter_excludes_dev_and_clean_rows():
    rows = [
        {"pipeline": pipeline, "variant_id": variant, "split": split, "noise_mode": mode, "condition_level": condition}
        for pipeline in ("P0", "P1", "P2")
        for variant, split, mode, condition in (
            ("clean", "test", "none", "C0"),
            ("dev-noise", "dev", "external_asset", "C2"),
            ("test-noise", "test", "external_asset", "C2"),
        )
    ]
    config = {"evaluation": {"primary_evidence_filter": {
        "split": "test",
        "noise_mode": "external_asset",
        "conditions": ["C1", "C2", "C3"],
        "expected_variants_per_pipeline": 1,
    }}}
    primary, applied = primary_evidence_rows(rows, config)
    assert applied is not None
    assert len(primary) == 3
    assert {row["variant_id"] for row in primary} == {"test-noise"}
    assert all(row["evidence_layer"] == "primary_recorded_noise_test" for row in primary)


def test_two_way_cluster_bootstrap_and_source_sensitivity_are_explicit():
    paired_rows = [
        {"base_id": 1, "noise_source_recording_id": "n1", "difference": -0.2},
        {"base_id": 1, "noise_source_recording_id": "n2", "difference": 0.0},
        {"base_id": 2, "noise_source_recording_id": "n1", "difference": -0.1},
        {"base_id": 2, "noise_source_recording_id": "n2", "difference": 0.1},
    ]
    bootstrap = two_way_cluster_bootstrap(
        paired_rows,
        value_field="difference",
        first_cluster="base_id",
        second_cluster="noise_source_recording_id",
        iterations=100,
        seed=11,
    )
    assert bootstrap["method"] == "pigeonhole_two_way_cluster_bootstrap"
    assert bootstrap["first_cluster_count"] == 2
    assert bootstrap["second_cluster_count"] == 2

    rows = []
    for variant, base_id, source, p0, p1 in (
        ("v1", 1, "n1", 0.4, 0.2),
        ("v2", 2, "n2", 0.2, 0.3),
    ):
        common = {"variant_id": variant, "base_id": base_id, "noise_source_recording_id": source, "noise_type": "fan"}
        rows.extend([{**common, "pipeline": "P0", "wer": p0}, {**common, "pipeline": "P1", "wer": p1}])
    sensitivity = paired_noise_source_sensitivity(rows, "P1", iterations=50, seed=5)
    assert sensitivity["paired_variants"] == 2
    assert sensitivity["noise_sources"] == 2
    assert sensitivity["two_way_cluster_bootstrap"]["availability"] == "available"


def test_report_renders_recorded_noise_primary_evidence(tmp_path):
    source = resolve_path(
        "dataset_benchmark/robustness_v2/reports_full/robustness_v2_summary.json"
    )
    summary = json.loads(source.read_text(encoding="utf-8"))
    summary["dataset"].update(
        {
            "conditions": ["C1", "C2", "C3"],
            "independent_base_utterances": 104,
            "audio_variants": 416,
            "pipeline_records": 1248,
            "run_audio_variants": 650,
            "run_pipeline_records": 1950,
            "unique_noise_sources": 28,
            "primary_filter": {"split": "test", "noise_mode": "external_asset"},
            "evaluated_base_ids": list(range(101, 205)),
        }
    )
    summary["statistics"]["noise_source_sensitivity"] = {
        candidate: {
            "noise_sources": 28,
            "two_way_cluster_bootstrap": {"ci_low": -0.01, "ci_high": 0.005},
        }
        for candidate in ("P1", "P2")
    }
    path = tmp_path / "recorded-summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    report = generate({"outputs": {"evaluation_summary": str(path)}})
    assert "held-out test subset of owner-recorded" in report
    assert "Independent test noise sources: 28" in report
    assert "Noise-source sensitivity" in report
    assert "10-base C0 pilot only" not in report

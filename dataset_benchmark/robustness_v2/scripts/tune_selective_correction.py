"""Tune the heuristic selective-correction threshold on dev data only."""

from __future__ import annotations

import argparse
import json

from dataset_benchmark.robustness_v2.error_analysis import build_stage_metadata
from dataset_benchmark.robustness_v2.pipeline import canonical_hash, tune_thresholds
from dataset_benchmark.scripts.common import (
    atomic_write_json,
    read_jsonl,
    resolve_path,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="dataset_benchmark/robustness_v2/configs/benchmark_v2_config.json",
    )
    args = parser.parse_args()
    config_path = resolve_path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    cache_dir = resolve_path(config["outputs"]["cache_dir"])
    risk_path = cache_dir / "risk_decisions.jsonl"
    correction_path = cache_dir / "corrections.jsonl"
    stt_path = cache_dir / "stt.jsonl"
    manifest_path = resolve_path(config["dataset"]["variant_manifest"])
    risks = {row["cache_id"]: row for row in read_jsonl(risk_path)}
    corrections = {row["cache_id"]: row for row in read_jsonl(correction_path)}
    stt = {row["cache_id"]: row for row in read_jsonl(stt_path)}
    manifest = {row["variant_id"]: row for row in read_jsonl(manifest_path)}
    required_split = config["threshold_tuning"]["split"]
    if required_split != "dev":
        raise ValueError("Threshold tuning is locked to dev; test tuning is forbidden")
    rows = []
    for cache_id, risk in risks.items():
        source = stt.get(cache_id)
        correction = corrections.get(cache_id)
        variant = manifest.get(cache_id)
        if not source or not correction or not variant or variant["split"] != "dev":
            continue
        rows.append(
            {
                "base_id": source["base_id"],
                "risk_score": risk["risk_score"],
                "raw_transcript": source["raw_transcript"],
                "corrected_transcript": correction["corrected_transcript"],
                "reference_transcript": variant["reference_transcript"],
            }
        )
    tuning = config["threshold_tuning"]
    candidates = tune_thresholds(
        rows,
        tuning["thresholds"],
        lambda_cost=float(tuning["lambda_cost"]),
        lambda_overcorrection=float(tuning["lambda_overcorrection"]),
    )
    configured_threshold = float(config["risk_detector"]["threshold"])
    configured_candidate = min(
        candidates,
        key=lambda row: abs(float(row["threshold"]) - configured_threshold),
    )
    inconclusive = (
        len(rows) < int(tuning["minimum_dev_samples"])
        or len({round(float(row["objective"]), 12) for row in candidates}) == 1
    )
    result = {
        "schema_version": "1.0.0",
        "split": required_split,
        "test_data_used_for_tuning": False,
        "samples": len(rows),
        "objective": tuning["objective"],
        "lambda_cost": tuning["lambda_cost"],
        "lambda_overcorrection": tuning["lambda_overcorrection"],
        "selection_status": (
            "inconclusive_keep_configured_threshold"
            if inconclusive
            else "tuned_on_dev"
        ),
        "minimum_dev_samples": tuning["minimum_dev_samples"],
        "selected": configured_candidate if inconclusive else candidates[0],
        "candidates": candidates,
        "config_hash": canonical_hash(config),
        "input_hashes": build_stage_metadata(
            "tune_selective_correction",
            inputs={
                "config": config_path,
                "variant_manifest": manifest_path,
                "stt_cache": stt_path,
                "risk_cache": risk_path,
                "correction_cache": correction_path,
            },
        )["inputs"],
    }
    output = resolve_path(config["outputs"]["threshold_tuning"])
    atomic_write_json(output, result)
    print(output)


if __name__ == "__main__":
    main()

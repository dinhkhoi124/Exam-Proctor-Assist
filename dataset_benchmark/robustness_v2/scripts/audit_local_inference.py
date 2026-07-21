"""Audit full local-inference caches, provenance, record counts, and actual cost."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import wave

from dataset_benchmark.robustness_v2.error_analysis import build_stage_metadata
from dataset_benchmark.robustness_v2.pipeline import canonical_hash
from dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark import (
    cache_path,
    load_config,
    validate_config,
)
from dataset_benchmark.scripts.common import atomic_write_json, read_jsonl, resolve_path


def _token_cost(rows: list[dict], config: dict) -> float:
    price = config["cost"]["models"]["gpt-4o-mini"]
    input_tokens = sum(int(row.get("prompt_tokens") or 0) for row in rows if row.get("cache_origin") == "api")
    output_tokens = sum(int(row.get("completion_tokens") or 0) for row in rows if row.get("cache_origin") == "api")
    return (
        input_tokens * price["input_per_million_tokens"]
        + output_tokens * price["output_per_million_tokens"]
    ) / 1_000_000


def audit(config: dict, config_path: Path) -> dict:
    validate_config(config, config_path)
    run_manifest_path = resolve_path(config["outputs"]["run_manifest"])
    manifest = read_jsonl(run_manifest_path)
    expected_variants = len(manifest)
    expected_pipeline_rows = expected_variants * len(config["pipelines"])
    caches = {
        "stt": read_jsonl(cache_path(config, "stt")),
        "risk_decisions": read_jsonl(cache_path(config, "risk_decisions")),
        "corrections": read_jsonl(cache_path(config, "corrections")),
        "retrieval": read_jsonl(cache_path(config, "retrieval")),
        "final_answers": read_jsonl(cache_path(config, "final_answers")),
        "judge": read_jsonl(cache_path(config, "judge")),
    }
    expected = {
        "stt": expected_variants,
        "risk_decisions": expected_variants,
        "corrections": expected_variants,
        "retrieval": expected_pipeline_rows,
        "final_answers": expected_pipeline_rows,
        "judge": expected_pipeline_rows,
    }
    counts = {
        name: {
            "expected": expected[name],
            "actual": len(rows),
            "api_origin": sum(row.get("cache_origin") == "api" for row in rows),
            "failed_or_excluded": sum(
                row.get("status") not in {None, "success", "imported", "skipped", "not_requested"}
                for row in rows
            ),
        }
        for name, rows in caches.items()
    }
    stt_api_ids = {
        row["variant_id"] for row in caches["stt"] if row.get("cache_origin") == "api"
    }
    stt_minutes = 0.0
    for row in manifest:
        if row["variant_id"] not in stt_api_ids:
            continue
        with wave.open(str(Path(row["output_audio_path"])), "rb") as handle:
            stt_minutes += handle.getnframes() / handle.getframerate() / 60
    stt_cost = stt_minutes * float(
        config["cost"]["models"]["gpt-4o-mini-transcribe"]["per_minute_assumption"]
    )
    correction_cost = _token_cost(caches["corrections"], config)
    answer_cost = _token_cost(caches["final_answers"], config)
    judge_cost = _token_cost(caches["judge"], config)
    checkpoint_dir = resolve_path(config["outputs"]["checkpoint_dir"])
    config_hash = canonical_hash(config)
    provenance = {}
    for stage in (
        "validate_config",
        "build_manifest",
        "generate_augmentation",
        "stt",
        "risk_detection",
        "correction",
        "retrieval",
        "final_answers",
        "judge",
        "evaluate",
        "report",
    ):
        path = checkpoint_dir / f"{stage}.metadata.json"
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        provenance[stage] = {
            "metadata_exists": path.exists(),
            "config_hash_match": payload.get("details", {}).get("config_hash") == config_hash,
        }
    required_variants = int(config["dataset"].get("expected_variants", 1040))
    verified = (
        expected_variants == required_variants
        and all(item["actual"] == item["expected"] for item in counts.values())
        and all(item["config_hash_match"] for item in provenance.values())
    )
    report = {
        "schema_version": "1.0.0",
        "config_hash": config_hash,
        "expected_variants": expected_variants,
        "required_variants": required_variants,
        "expected_pipeline_rows": expected_pipeline_rows,
        "cache_counts": counts,
        "actual_cost_usd": {
            "stt": round(stt_cost, 6),
            "correction": round(correction_cost, 6),
            "final_answers": round(answer_cost, 6),
            "judge": round(judge_cost, 6),
            "total": round(stt_cost + correction_cost + answer_cost + judge_cost, 6),
        },
        "stt_billable_minutes": round(stt_minutes, 3),
        "provenance": provenance,
        "verified": verified,
        "api_calls_performed_by_audit": 0,
    }
    output = resolve_path(config["outputs"].get(
        "local_inference_audit",
        "dataset_benchmark/robustness_v2/reports_full/local_inference_audit.json",
    ))
    atomic_write_json(output, report)
    metadata = build_stage_metadata(
        "audit_local_inference",
        inputs={
            "config": config_path,
            "run_manifest": run_manifest_path,
            **{name: cache_path(config, name) for name in caches},
        },
        outputs={"audit_report": output},
        details={"config_hash": config_hash, "api_calls": 0},
    )
    atomic_write_json(checkpoint_dir / "local_inference_audit.metadata.json", metadata)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="dataset_benchmark/robustness_v2/configs/local_full_inference_config.json",
    )
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    config_path = resolve_path(args.config)
    config = load_config(config_path)
    report = audit(config, config_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.strict and not report["verified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

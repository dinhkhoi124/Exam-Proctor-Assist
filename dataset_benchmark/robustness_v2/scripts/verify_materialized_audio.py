"""Verify materialized WAV inventory and hashes against the generated manifest."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random

from dataset_benchmark.robustness_v2.error_analysis import build_stage_metadata
from dataset_benchmark.robustness_v2.pipeline import canonical_hash
from dataset_benchmark.scripts.common import (
    atomic_write_json,
    read_jsonl,
    resolve_path,
    sha256_file,
)


def verify(config: dict, config_path: Path, *, sample_size: int, sample_seed: int) -> dict:
    manifest_path = resolve_path(config["generated_manifest"])
    audio_dir = resolve_path(config["output_audio_dir"]).resolve()
    rows = read_jsonl(manifest_path)
    actual_files = sorted(path.resolve() for path in audio_dir.rglob("*.wav"))
    expected_materialized: set[Path] = set()
    missing: list[str] = []
    mismatches: list[dict] = []
    verified: list[dict] = []
    for row in rows:
        path = Path(row["output_audio_path"]).resolve()
        if path == audio_dir or audio_dir in path.parents:
            expected_materialized.add(path)
        if not path.exists():
            missing.append(row["variant_id"])
            continue
        actual_hash = sha256_file(path)
        expected_hash = row.get("output_audio_sha256")
        item = {
            "variant_id": row["variant_id"],
            "condition_level": row["condition_level"],
            "path": str(path),
            "manifest_sha256": expected_hash,
            "actual_sha256": actual_hash,
            "match": actual_hash == expected_hash,
        }
        verified.append(item)
        if not item["match"]:
            mismatches.append(item)

    rng = random.Random(sample_seed)
    materialized_verified = [item for item in verified if Path(item["path"]) in expected_materialized]
    sampled = rng.sample(materialized_verified, min(sample_size, len(materialized_verified)))
    unexpected = sorted(str(path) for path in set(actual_files) - expected_materialized)
    missing_materialized = sorted(str(path) for path in expected_materialized - set(actual_files))
    report = {
        "schema_version": "1.0.0",
        "augmentation_config_hash": canonical_hash(config),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "manifest_rows": len(rows),
        "condition_distribution": dict(Counter(row["condition_level"] for row in rows)),
        "split_distribution": dict(Counter(row["split"] for row in rows)),
        "audio_augmented_wav_count": len(actual_files),
        "audio_augmented_bytes": sum(path.stat().st_size for path in actual_files),
        "all_output_wav_count": len(verified),
        "all_output_bytes": sum(Path(item["path"]).stat().st_size for item in verified),
        "expected_materialized_wav_count": len(expected_materialized),
        "missing_variant_ids": missing,
        "missing_materialized_paths": missing_materialized,
        "unexpected_audio_augmented_paths": unexpected,
        "full_hash_verification": {
            "checked": len(verified),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        },
        "random_hash_sample": {
            "sampling_unit": "C1-C3 materialized WAV",
            "seed": sample_seed,
            "requested_size": sample_size,
            "actual_size": len(sampled),
            "rows": sampled,
        },
        "verified": not missing and not missing_materialized and not unexpected and not mismatches,
        "api_calls": 0,
    }
    report_path = resolve_path(config.get(
        "materialization_verification_output",
        "dataset_benchmark/robustness_v2/reports/materialization_verification.json",
    ))
    atomic_write_json(report_path, report)
    metadata = build_stage_metadata(
        "verify_materialized_audio",
        inputs={"config": config_path, "generated_manifest": manifest_path},
        outputs={"verification_report": report_path},
        details={
            "config_hash": canonical_hash(config),
            "checked_wav_files": len(verified),
            "api_calls": 0,
        },
    )
    checkpoint_dir = resolve_path(config.get(
        "checkpoint_dir", "dataset_benchmark/robustness_v2/checkpoints"
    ))
    atomic_write_json(checkpoint_dir / "materialization_verification.metadata.json", metadata)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="dataset_benchmark/robustness_v2/configs/augmentation_config.json",
    )
    parser.add_argument("--sample-size", type=int, default=25)
    parser.add_argument("--sample-seed", type=int, default=20260719)
    args = parser.parse_args()
    config_path = resolve_path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    report = verify(
        config,
        config_path,
        sample_size=args.sample_size,
        sample_seed=args.sample_seed,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["verified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

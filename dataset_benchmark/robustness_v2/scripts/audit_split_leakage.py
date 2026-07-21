"""Audit v2 manifest for split leakage."""

from __future__ import annotations

import argparse
import json

from dataset_benchmark.robustness_v2.error_analysis import build_stage_metadata
from dataset_benchmark.robustness_v2.pipeline import canonical_hash
from dataset_benchmark.robustness_v2.split import audit_leakage
from dataset_benchmark.robustness_v2.scripts.generate_augmented_dataset import (
    validate_output_paths,
)
from dataset_benchmark.scripts.common import (
    atomic_write_json,
    read_jsonl,
    resolve_path,
    sha256_file,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="dataset_benchmark/robustness_v2/configs/augmentation_config.json",
    )
    parser.add_argument("--manifest", default=None)
    args = parser.parse_args()
    config_path = resolve_path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_output_paths(config)
    manifest = resolve_path(args.manifest or config["planned_manifest"])
    rows = read_jsonl(manifest)
    if not rows:
        parser.error(f"Manifest is missing or empty: {manifest}")
    result = audit_leakage(
        rows,
        near_duplicate_threshold=float(
            config["split"]["near_duplicate_jaccard_threshold"]
        ),
        prompt_examples=config.get("prompt_few_shot_examples", []),
    )
    result.update(
        {
            "schema_version": "1.0.0",
            "audited_manifest": str(manifest),
            "audited_manifest_sha256": sha256_file(manifest),
            "audited_rows": len(rows),
            "config_hash": canonical_hash(config),
        }
    )
    output = resolve_path(config["leakage_audit_output"])
    atomic_write_json(output, result)
    metadata = build_stage_metadata(
        "audit_split_leakage",
        inputs={"config": config_path, "manifest": manifest},
        outputs={"leakage_audit": output},
        details={
            "config_hash": canonical_hash(config),
            "audited_rows": len(rows),
            "leakage_detected": result["leakage_detected"],
            "api_calls": 0,
        },
    )
    checkpoint_dir = resolve_path(config.get(
        "checkpoint_dir", "dataset_benchmark/robustness_v2/checkpoints"
    ))
    atomic_write_json(checkpoint_dir / "split_leakage_audit.metadata.json", metadata)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["leakage_detected"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

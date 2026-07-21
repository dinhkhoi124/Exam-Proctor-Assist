"""Quality-gate materialized owner-recorded noise mixtures before paid inference."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np

from dataset_benchmark.robustness_v2.augmentation import read_wav, rms
from dataset_benchmark.robustness_v2.error_analysis import build_stage_metadata
from dataset_benchmark.robustness_v2.pipeline import canonical_hash
from dataset_benchmark.scripts.common import (
    atomic_write_json,
    read_jsonl,
    resolve_path,
)


def _estimate_snr(clean: np.ndarray, noisy: np.ndarray) -> tuple[float, float]:
    length = min(len(clean), len(noisy))
    clean = clean[:length].astype(np.float64)
    noisy = noisy[:length].astype(np.float64)
    scale = float(np.dot(noisy, clean) / max(np.dot(clean, clean), 1e-20))
    residual = noisy - scale * clean
    estimate = 20.0 * math.log10(
        max(rms(scale * clean), 1e-20) / max(rms(residual), 1e-20)
    )
    return estimate, rms(residual)


def audit(config: dict, config_path: Path) -> dict:
    manifest_path = resolve_path(config["generated_manifest"])
    rows = read_jsonl(manifest_path)
    noise_rows = [row for row in rows if row.get("noise_path")]
    details = []
    for row in noise_rows:
        clean = read_wav(Path(row["source_audio_path"])).samples
        output = read_wav(Path(row["output_audio_path"])).samples
        estimated_snr, residual_rms = _estimate_snr(clean, output)
        target_snr = float(row["snr_db"])
        clipped_fraction = float(np.mean(np.abs(output) >= 0.999)) if len(output) else 0.0
        details.append(
            {
                "variant_id": row["variant_id"],
                "base_id": row["base_id"],
                "split": row["split"],
                "noise_type": row["noise_type"],
                "noise_source_recording_id": row["noise_source_recording_id"],
                "noise_asset_id": row["noise_asset_id"],
                "target_snr_db": target_snr,
                "estimated_signal_relative_snr_db": round(estimated_snr, 6),
                "absolute_snr_error_db": round(abs(estimated_snr - target_snr), 6),
                "residual_rms": round(residual_rms, 9),
                "clipped_fraction": round(clipped_fraction, 9),
                "crop_wrap_count": int((row.get("noise_crop") or {}).get("wrap_count", 0)),
                "output_audio_path": row["output_audio_path"],
            }
        )
    errors = [row["absolute_snr_error_db"] for row in details]
    residuals = [row["residual_rms"] for row in details]
    clipped = [row["clipped_fraction"] for row in details]
    source_splits: dict[str, set[str]] = {}
    for row in details:
        source_splits.setdefault(row["noise_source_recording_id"], set()).add(row["split"])
    source_leaks = sorted(key for key, splits in source_splits.items() if len(splits) > 1)
    verified = (
        len(rows) == 650
        and len(noise_rows) == 520
        and all(row.get("status") == "success" for row in rows)
        and max(errors, default=math.inf) <= 0.5
        and min(residuals, default=0.0) > 1e-4
        and max(clipped, default=1.0) <= 1e-4
        and not source_leaks
    )
    report = {
        "schema_version": "1.0.0",
        "config_hash": canonical_hash(config),
        "manifest": str(manifest_path),
        "manifest_rows": len(rows),
        "noise_rows": len(noise_rows),
        "condition_distribution": dict(Counter(row["condition_level"] for row in rows)),
        "noise_type_distribution": dict(Counter(row["noise_type"] for row in noise_rows)),
        "snr_distribution": dict(Counter(str(row["target_snr_db"]) for row in details)),
        "unique_noise_sources": len(source_splits),
        "cross_split_noise_source_ids": source_leaks,
        "snr_error_db": {
            "p50": round(float(np.percentile(errors, 50)), 6),
            "p95": round(float(np.percentile(errors, 95)), 6),
            "maximum": round(max(errors), 6),
            "allowed_maximum": 0.5,
        },
        "minimum_residual_rms": round(min(residuals), 9),
        "maximum_clipped_fraction": round(max(clipped), 9),
        "wrapped_crop_rows": sum(row["crop_wrap_count"] > 0 for row in details),
        "quality_gate": {
            "all_noise_rows_audibly_nonidentical_proxy": min(residuals) > 1e-4,
            "target_snr_within_tolerance": max(errors) <= 0.5,
            "no_material_clipping": max(clipped) <= 1e-4,
            "noise_sources_split_disjoint": not source_leaks,
        },
        "verified": verified,
        "rows": details,
        "api_calls": 0,
    }
    report_path = resolve_path(config["quality_audit_output"])
    atomic_write_json(report_path, report)
    listening_rows = [row for row in rows if int(row["base_id"]) == 101]
    lines = [
        "# Recorded-noise listening samples",
        "",
        "Listen in order. C0 is the clean source; C1-C3 contain owner-recorded noise.",
        "",
    ]
    for row in listening_rows:
        path = Path(row["output_audio_path"]).resolve()
        label = f"{row['condition_level']} — {row.get('noise_type') or 'clean'}"
        if row.get("snr_db") is not None:
            label += f" — target SNR {row['snr_db']} dB"
        lines.append(f"- [{label}]({path.as_posix()})")
    listening_path = resolve_path(config["listening_index_output"])
    listening_path.parent.mkdir(parents=True, exist_ok=True)
    listening_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    metadata = build_stage_metadata(
        "audit_recorded_noise_audio",
        inputs={"config": config_path, "generated_manifest": manifest_path},
        outputs={"quality_audit": report_path, "listening_index": listening_path},
        details={"config_hash": canonical_hash(config), "verified": verified, "api_calls": 0},
    )
    atomic_write_json(
        resolve_path(config["checkpoint_dir"]) / "audio_quality_audit.metadata.json",
        metadata,
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="dataset_benchmark/robustness_v2/configs/augmentation_recorded_noise_config.json",
    )
    args = parser.parse_args()
    config_path = resolve_path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    report = audit(config, config_path)
    printable = {key: value for key, value in report.items() if key != "rows"}
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    if not report["verified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

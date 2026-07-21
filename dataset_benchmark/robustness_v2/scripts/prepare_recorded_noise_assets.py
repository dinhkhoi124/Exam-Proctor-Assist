"""Validate recorded M4A pools and convert them to normalized benchmark WAV assets."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np

from dataset_benchmark.robustness_v2.augmentation import read_wav, rms
from dataset_benchmark.scripts.common import atomic_write_json, resolve_path, sha256_file


CATEGORIES = ("fan", "cafe", "office", "speech_babble")
EXPECTED_COUNTS = {"dev": 3, "test": 7}


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def prepare(raw_root: Path, output_root: Path, report_path: Path) -> dict:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to decode recorded M4A assets")
    sources = []
    for split, expected in EXPECTED_COUNTS.items():
        for category in CATEGORIES:
            files = sorted((raw_root / split / category).glob("*.m4a"))
            if len(files) != expected:
                raise ValueError(
                    f"Expected {expected} {split}/{category} M4A files, found {len(files)}"
                )
            for path in files:
                sources.append(
                    {
                        "split": split,
                        "category": category,
                        "path": path,
                        "raw_sha256": sha256_file(path),
                    }
                )
    by_raw_hash: dict[str, set[str]] = defaultdict(set)
    for row in sources:
        by_raw_hash[row["raw_sha256"]].add(row["split"])
    raw_leaks = sorted(digest for digest, pools in by_raw_hash.items() if len(pools) > 1)
    if raw_leaks:
        raise ValueError(f"Recorded noise raw hashes cross dev/test: {raw_leaks}")

    manifest = []
    for index, source in enumerate(sources, start=1):
        short_hash = source["raw_sha256"][:12]
        asset_id = f"recorded_{source['split']}_{source['category']}_{index:02d}_{short_hash}"
        target = output_root / source["split"] / source["category"] / f"{asset_id}.wav"
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".wav.tmp.wav")
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source["path"]),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(temporary),
            ],
            check=True,
        )
        temporary.replace(target)
        audio = read_wav(target)
        level = rms(audio.samples)
        peak = float(np.max(np.abs(audio.samples))) if len(audio.samples) else 0.0
        if len(audio.samples) == 0 or level <= 1e-6:
            raise ValueError(f"Recorded noise is empty or silent: {source['path']}")
        manifest.append(
            {
                "asset_id": asset_id,
                "category": source["category"],
                "split_pool": source["split"],
                "source_recording_id": f"owner_recording_{source['raw_sha256']}",
                "path": str(target),
                "license": "project_owner_recorded_for_benchmark",
                "source": "project_owner_recording",
                "original_path": str(source["path"]),
                "original_sha256": source["raw_sha256"],
                "wav_sha256": sha256_file(target),
                "duration_sec": round(len(audio.samples) / audio.sample_rate, 6),
                "sample_rate": audio.sample_rate,
                "channels": 1,
                "rms": round(level, 9),
                "peak": round(peak, 9),
            }
        )
    by_wav_hash: dict[str, set[str]] = defaultdict(set)
    for row in manifest:
        by_wav_hash[row["wav_sha256"]].add(row["split_pool"])
    decoded_leaks = sorted(
        digest for digest, pools in by_wav_hash.items() if len(pools) > 1
    )
    if decoded_leaks:
        raise ValueError(f"Decoded WAV hashes cross dev/test: {decoded_leaks}")

    manifest_path = output_root / "manifest.csv"
    _write_csv(manifest_path, manifest)
    report = {
        "schema_version": "1.0.0",
        "raw_root": str(raw_root),
        "output_root": str(output_root),
        "manifest": str(manifest_path),
        "asset_count": len(manifest),
        "unique_raw_hashes": len({row["original_sha256"] for row in manifest}),
        "unique_wav_hashes": len({row["wav_sha256"] for row in manifest}),
        "cross_split_raw_hashes": raw_leaks,
        "cross_split_wav_hashes": decoded_leaks,
        "counts": dict(sorted(Counter(
            f"{row['split_pool']}:{row['category']}" for row in manifest
        ).items())),
        "duration_seconds": {
            key: round(sum(row["duration_sec"] for row in manifest if f"{row['split_pool']}:{row['category']}" == key), 6)
            for key in sorted({f"{row['split_pool']}:{row['category']}" for row in manifest})
        },
        "minimum_rms": min(row["rms"] for row in manifest),
        "maximum_peak": max(row["peak"] for row in manifest),
        "verified": len(manifest) == 40 and not raw_leaks and not decoded_leaks,
    }
    atomic_write_json(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-root",
        default="dataset_benchmark/robustness_v2/assets/recorded_noise",
    )
    parser.add_argument(
        "--output-root",
        default="dataset_benchmark/robustness_v2/assets/recorded_noise_wav",
    )
    parser.add_argument(
        "--report",
        default="dataset_benchmark/robustness_v2/reports_recorded_noise/asset_audit.json",
    )
    args = parser.parse_args()
    report = prepare(
        resolve_path(args.raw_root),
        resolve_path(args.output_root),
        resolve_path(args.report),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["verified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

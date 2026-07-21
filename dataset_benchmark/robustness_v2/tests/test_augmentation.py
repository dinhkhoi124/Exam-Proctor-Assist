import json
from pathlib import Path
import wave

import numpy as np

from dataset_benchmark.robustness_v2.augmentation import (
    AudioData,
    add_background_noise,
    apply_crop_plan,
    audio_sha256,
    augment_file,
    generate_image_source_rir,
    generate_procedural_noise,
    measured_snr_db,
    plan_crop,
    read_wav,
    write_wav,
)
from dataset_benchmark.robustness_v2.scripts.generate_augmented_dataset import (
    dry_run_summary,
    generate,
    load_asset_manifest,
    plan_variants,
    validate_asset_pools,
    validate_output_paths,
    write_variant_jsonl,
)
from dataset_benchmark.scripts.common import read_jsonl


def _tone(rate=16000, seconds=0.2, frequency=440.0, amplitude=0.3):
    time = np.arange(round(rate * seconds)) / rate
    return AudioData((amplitude * np.sin(2 * np.pi * frequency * time)).astype(np.float32), rate)


def test_background_noise_hits_configured_snr():
    clean = _tone().samples
    noise = _tone(frequency=997.0, amplitude=0.2).samples
    import random

    mixed = add_background_noise(clean, noise, 10.0, random.Random(7))
    assert abs(measured_snr_db(clean, mixed) - 10.0) < 0.05


def test_augmentation_is_hash_reproducible_and_duration_safe(tmp_path):
    source = tmp_path / "source.wav"
    noise = tmp_path / "noise.wav"
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    write_wav(source, _tone())
    write_wav(noise, _tone(frequency=997.0))
    operations = [
        {"name": "background_noise", "snr_db": 10},
        {"name": "bandpass_phone"},
        {"name": "codec_compression", "bits": 8},
    ]
    first_meta = augment_file(source, first, operations, seed=11, noise_path=noise)
    second_meta = augment_file(source, second, operations, seed=11, noise_path=noise)
    assert first_meta["output_audio_sha256"] == second_meta["output_audio_sha256"]
    assert first_meta["output_duration_sec"] == second_meta["output_duration_sec"]
    assert first_meta["peak"] <= 0.9991


def test_speed_and_clipping_are_explicit(tmp_path):
    source = tmp_path / "source.wav"
    output = tmp_path / "output.wav"
    write_wav(source, _tone(amplitude=0.95))
    metadata = augment_file(
        source,
        output,
        [{"name": "mild_clipping", "threshold": 0.5}, {"name": "speed_1_1", "factor": 1.1}],
        seed=5,
    )
    assert metadata["peak"] <= 0.501
    assert metadata["output_duration_sec"] < metadata["source_duration_sec"]


def test_resample_8k_roundtrip_preserves_duration_and_output_rate(tmp_path):
    source = tmp_path / "source.wav"
    output = tmp_path / "output.wav"
    write_wav(source, _tone())
    metadata = augment_file(source, output, [{"name": "resample_8k"}], seed=5)
    assert metadata["output_duration_sec"] == metadata["source_duration_sec"]
    assert read_wav(output).sample_rate == 16000


def test_rir_fixture_preserves_configured_length(tmp_path):
    source = tmp_path / "source.wav"
    rir = tmp_path / "rir.wav"
    output = tmp_path / "output.wav"
    write_wav(source, _tone())
    impulse = np.zeros(320, dtype=np.float32)
    impulse[0], impulse[100] = 1.0, 0.3
    write_wav(rir, AudioData(impulse, 16000))
    metadata = augment_file(
        source,
        output,
        [{"name": "room_reverberation"}],
        seed=1,
        rir_path=rir,
    )
    assert metadata["source_duration_sec"] == metadata["output_duration_sec"]


def test_dry_run_planning_does_not_create_output(tmp_path):
    source = tmp_path / "source.wav"
    write_wav(source, _tone())
    config = {
        "version": "2",
        "global_seed": 7,
        "noise_asset_manifest": str(tmp_path / "missing-noise.csv"),
        "rir_asset_manifest": str(tmp_path / "missing-rir.csv"),
        "output_audio_dir": str(tmp_path / "outputs"),
        "split": {"near_duplicate_jaccard_threshold": 0.8},
        "conditions": {
            "C0": {"enabled": True, "variants_per_base": 1, "chains": [{"id": "original", "operations": []}]},
            "C1": {"enabled": True, "variants_per_base": 1, "chains": [{"id": "noise", "operations": [{"name": "background_noise", "noise_type": "fan", "snr_db": 15}]}]},
        },
    }
    manifest = [{"audio_id": "1", "audio_path": str(source), "speaker": "A", "reference_transcript": "nội quy", "eligibility_status": "eligible", "split": "dev"}]
    first = plan_variants(config, manifest)
    second = plan_variants(config, manifest)
    assert first == second
    summary = dry_run_summary(first)
    assert summary["planned_variants"] == 2
    assert summary["missing_assets"] == {"noise:fan:dev": 1}
    assert not (tmp_path / "outputs").exists()


def test_variant_manifest_writer_uses_base_and_variant_ids(tmp_path):
    target = tmp_path / "manifest.jsonl"
    write_variant_jsonl(
        target,
        [
            {"base_id": 2, "variant_id": "2_b"},
            {"base_id": 1, "variant_id": "1_a"},
        ],
    )
    assert read_jsonl(target) == [
        {"base_id": 1, "variant_id": "1_a"},
        {"base_id": 2, "variant_id": "2_b"},
    ]


def test_v2_output_paths_cannot_point_to_v1():
    config = {
        "base_manifest_snapshot": "dataset_benchmark/robustness_v2/manifests/base.jsonl",
        "output_audio_dir": "dataset_benchmark/robustness_v2/audio_augmented",
        "planned_manifest": "dataset_benchmark/benchmark_outputs/plan.jsonl",
        "generated_manifest": "dataset_benchmark/robustness_v2/manifests/generated.jsonl",
        "leakage_audit_output": "dataset_benchmark/robustness_v2/reports/audit.json",
    }
    import pytest

    with pytest.raises(ValueError, match="planned_manifest must resolve under"):
        validate_output_paths(config)


def test_procedural_noise_is_seeded_and_split_realizations_differ():
    parameters = {
        "color": "pink",
        "fundamental_hz": 50,
        "harmonics": 5,
        "modulation_hz": 0.4,
        "modulation_depth": 0.12,
    }
    first = generate_procedural_noise(
        "synthetic_fan_proxy", 3200, 16000, seed=11, parameters=parameters
    )
    repeated = generate_procedural_noise(
        "synthetic_fan_proxy", 3200, 16000, seed=11, parameters=parameters
    )
    held_out = generate_procedural_noise(
        "synthetic_fan_proxy", 3200, 16000, seed=12, parameters=parameters
    )
    assert audio_sha256(first) == audio_sha256(repeated)
    assert audio_sha256(first) != audio_sha256(held_out)
    assert abs(np.mean(first.samples)) < 1e-5
    assert np.sqrt(np.mean(first.samples**2)) > 0.1


def test_babble_uses_recorded_crop_plans_deterministically():
    import random

    donors = []
    for index in range(4):
        donor = _tone(frequency=300 + 100 * index)
        crop = plan_crop(len(donor.samples), 2400, random.Random(index))
        assert len(apply_crop_plan(donor.samples, crop)) == 2400
        donors.append((donor, crop, 0.8 + index * 0.02))
    first = generate_procedural_noise(
        "in_corpus_speech_babble",
        2400,
        16000,
        seed=91,
        parameters={"donor_count": 4},
        donor_tracks=donors,
    )
    second = generate_procedural_noise(
        "in_corpus_speech_babble",
        2400,
        16000,
        seed=91,
        parameters={"donor_count": 4},
        donor_tracks=donors,
    )
    assert audio_sha256(first) == audio_sha256(second)


def test_image_source_rir_is_deterministic_non_silent_and_normalized():
    parameters = {
        "room_dimensions_m": [4.0, 5.0, 3.0],
        "source_position_m": [1.0, 1.5, 1.2],
        "microphone_position_m": [3.0, 3.0, 1.3],
        "rt60_sec": 0.4,
        "duration_sec": 0.5,
        "max_order": 3,
        "speed_of_sound_mps": 343.0,
    }
    first = generate_image_source_rir(16000, parameters=parameters)
    second = generate_image_source_rir(16000, parameters=parameters)
    assert audio_sha256(first) == audio_sha256(second)
    assert np.isfinite(first.samples).all()
    assert 0.99 <= np.sqrt(np.sum(first.samples**2)) <= 1.01
    assert np.count_nonzero(first.samples) > 1


def test_external_asset_hash_cannot_be_aliased_across_split_pools(tmp_path):
    import csv

    dev = tmp_path / "dev.wav"
    test = tmp_path / "test.wav"
    write_wav(dev, _tone())
    test.write_bytes(dev.read_bytes())
    manifest = tmp_path / "assets.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "asset_id",
                "category",
                "split_pool",
                "source_recording_id",
                "path",
                "license",
                "source",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "asset_id": "dev",
                "category": "fan",
                "split_pool": "dev",
                "source_recording_id": "dev_recording",
                "path": str(dev),
                "license": "owned",
                "source": "test",
            }
        )
        writer.writerow(
            {
                "asset_id": "test",
                "category": "fan",
                "split_pool": "test",
                "source_recording_id": "test_recording",
                "path": str(test),
                "license": "owned",
                "source": "test",
            }
        )
    assets = load_asset_manifest(manifest, "noise")
    import pytest

    with pytest.raises(ValueError, match="multiple split pools"):
        validate_asset_pools(assets, "noise")


def test_procedural_plan_generates_audio_without_external_assets(tmp_path):
    source = tmp_path / "source.wav"
    write_wav(source, _tone())
    config = {
        "version": "2",
        "global_seed": 9,
        "noise_asset_manifest": str(tmp_path / "missing-noise.csv"),
        "rir_asset_manifest": str(tmp_path / "missing-rir.csv"),
        "output_audio_dir": str(tmp_path / "outputs"),
        "procedural_generation": {
            "version": "test_v1",
            "evidence_tier": "controlled_synthetic_primary",
            "real_world_generalization_claim_allowed": False,
            "external_validation_status": "not_provided",
        },
        "split": {"near_duplicate_jaccard_threshold": 0.8},
        "conditions": {
            "C1": {
                "enabled": True,
                "variants_per_base": 1,
                "chains": [
                    {
                        "id": "fan",
                        "operations": [
                            {
                                "name": "background_noise",
                                "noise_type": "synthetic_fan_proxy",
                                "generator": "synthetic_fan_proxy",
                                "fundamental_hz": 50,
                                "snr_db": 15,
                            }
                        ],
                    }
                ],
            }
        },
    }
    manifest = [
        {
            "audio_id": "1",
            "audio_path": str(source),
            "speaker": "A",
            "reference_transcript": "nội quy",
            "eligibility_status": "eligible",
            "split": "dev",
        }
    ]
    planned = plan_variants(config, manifest)
    assert planned[0]["missing_assets"] == []
    generated = generate(planned, condition="C1")
    assert generated[0]["status"] == "success"
    assert generated[0]["noise_sha256"]
    assert Path(generated[0]["output_audio_path"]).is_file()

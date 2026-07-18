from pathlib import Path

from dataset_benchmark.scripts.build_manifest import build_manifest, clean_reference


ROOT = Path(__file__).resolve().parents[2]


def test_reference_cleanup_only_removes_terminal_artifact():
    assert clean_reference('Nội quy kỳ thi?"}') == "Nội quy kỳ thi?"
    assert clean_reference('Mã "ABC" vẫn giữ') == 'Mã "ABC" vẫn giữ'


def test_manifest_has_locked_counts(tmp_path):
    records = build_manifest(
        ROOT / "dataset_benchmark" / "AUDIO_299.xlsx",
        ROOT
        / "dataset_benchmark"
        / "Audio_wav-20260708T055213Z-3-001"
        / "Audio_wav",
        tmp_path / "manifest.csv",
    )
    eligible = [row for row in records if row["eligibility_status"] == "eligible"]
    assert len(records) == 299
    assert len(eligible) == 130
    assert {int(row["audio_id"]) for row in eligible} == set(range(101, 231))
    assert sum(row["split"] == "dev" for row in eligible) == 26
    assert sum(row["split"] == "test" for row in eligible) == 104
    assert sum(bool(row["human_eval"]) for row in eligible) == 60
    assert all(
        row["split"] == "test" for row in eligible if row["human_eval"]
    )
    reasons = {
        int(row["audio_id"]): row["exclusion_reason"]
        for row in records
        if row["eligibility_status"] == "excluded"
    }
    assert reasons[2] == "missing_reference"
    assert reasons[4] == "missing_reference"
    assert reasons[89] == "missing_audio"
    assert reasons[1] == "audio_reference_mismatch"
    assert reasons[100] == "audio_reference_mismatch"
    assert reasons[231] == "missing_audio"

    repeated = build_manifest(
        ROOT / "dataset_benchmark" / "AUDIO_299.xlsx",
        ROOT
        / "dataset_benchmark"
        / "Audio_wav-20260708T055213Z-3-001"
        / "Audio_wav",
        tmp_path / "manifest_repeated.csv",
    )
    assert [
        (row["audio_id"], row["split"], row["human_eval"]) for row in records
    ] == [
        (row["audio_id"], row["split"], row["human_eval"]) for row in repeated
    ]

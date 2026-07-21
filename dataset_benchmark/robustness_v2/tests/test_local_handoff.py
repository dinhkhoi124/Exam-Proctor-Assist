from argparse import Namespace
from pathlib import Path

import pytest

from dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark import (
    dry_run,
    load_config,
    require_paid_api_confirmation,
    replace_with_retry,
    selected_variants,
    validate_config,
    variant_audio_path,
)
from dataset_benchmark.scripts.common import resolve_path


CONFIG_PATH = resolve_path(
    "dataset_benchmark/robustness_v2/configs/local_full_inference_config.json"
)
HISTORICAL_FULL_MANIFEST = resolve_path(
    "dataset_benchmark/robustness_v2/manifests/augmentation_generated.jsonl"
)
HISTORICAL_FULL_AUDIO = resolve_path(
    "dataset_benchmark/robustness_v2/audio_augmented"
)


def _require_historical_full_fixture():
    if not HISTORICAL_FULL_MANIFEST.exists() or not HISTORICAL_FULL_AUDIO.exists():
        pytest.skip("historical synthetic full-run fixture is not part of Git-light handoff")


def _args(**overrides):
    values = {
        "condition": None,
        "base_id": None,
        "limit": None,
        "pipeline": None,
        "resume": False,
    }
    values.update(overrides)
    return Namespace(**values)


def test_local_full_config_inherits_locked_prompts_and_is_valid():
    _require_historical_full_fixture()
    config = load_config(CONFIG_PATH)
    assert "extends" not in config
    assert config["dataset"]["default_condition"] is None
    assert config["correction"]["prompt_sha256"]
    assert config["answer_generation"]["prompt_sha256"]
    assert config["judge"]["prompt_sha256"]
    validate_config(config, CONFIG_PATH)


def test_local_full_selection_contains_all_1040_variants():
    _require_historical_full_fixture()
    rows = selected_variants(load_config(CONFIG_PATH), _args())
    assert len(rows) == 1040
    assert len({row["base_id"] for row in rows}) == 130
    assert {row["condition_level"] for row in rows} == {"C0", "C1", "C2", "C3"}


def test_paid_api_gate_requires_exact_confirmation(monkeypatch):
    config = load_config(CONFIG_PATH)
    monkeypatch.delenv("ROBUSTNESS_V2_ALLOW_PAID_API", raising=False)
    with pytest.raises(RuntimeError, match="Paid API gate is closed"):
        require_paid_api_confirmation(config)
    monkeypatch.setenv("ROBUSTNESS_V2_ALLOW_PAID_API", "YES_I_REVIEWED_THE_FULL_COST")
    require_paid_api_confirmation(config)


def test_local_full_dry_run_counts_calls_without_writes():
    _require_historical_full_fixture()
    summary = dry_run(load_config(CONFIG_PATH), Path(CONFIG_PATH), _args())
    assert summary["audio_variants"] == 1040
    calls = summary["estimated_api_calls"]
    assert calls["stt"] == 910
    assert calls["correction"] == 910
    assert 0 <= calls["final_answers"] <= 3120
    assert 0 <= calls["judge"] <= 3120
    assert calls["total"] == sum(calls[name] for name in ("stt", "correction", "final_answers", "judge"))
    assert summary["writes_performed"] is False
    assert summary["paid_api_confirmation"]["required"] is True


def test_atomic_replace_retries_transient_windows_lock(monkeypatch, tmp_path):
    source = tmp_path / "cache.jsonl.tmp"
    target = tmp_path / "cache.jsonl"
    source.write_text("new", encoding="utf-8")
    target.write_text("old", encoding="utf-8")
    real_replace = __import__("os").replace
    calls = {"count": 0}

    def flaky_replace(temporary, destination):
        calls["count"] += 1
        if calls["count"] < 3:
            raise PermissionError(5, "transient lock")
        real_replace(temporary, destination)

    monkeypatch.setattr(
        "dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark.os.replace",
        flaky_replace,
    )
    replace_with_retry(source, target, attempts=4, base_delay_seconds=0)
    assert calls["count"] == 3
    assert target.read_text(encoding="utf-8") == "new"


def test_variant_audio_path_relocates_stale_clone_path(monkeypatch, tmp_path):
    relocated = tmp_path / "dataset_benchmark" / "audio" / "sample.wav"
    relocated.parent.mkdir(parents=True)
    relocated.write_bytes(b"wav")

    def fake_resolve(value):
        value = Path(value)
        if not value.is_absolute() and value.parts[:1] == ("dataset_benchmark",):
            return tmp_path / value
        return value

    monkeypatch.setattr(
        "dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark.resolve_path",
        fake_resolve,
    )
    row = {
        "output_audio_path": r"Z:\old-clone\dataset_benchmark\audio\sample.wav",
        "condition_level": "C1",
    }
    assert variant_audio_path({"dataset": {}}, row) == relocated

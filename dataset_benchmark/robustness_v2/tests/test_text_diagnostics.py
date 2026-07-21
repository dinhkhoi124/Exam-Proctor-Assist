import json

import pytest

from dataset_benchmark.robustness_v2.scripts.generate_text_diagnostics import generate
from dataset_benchmark.robustness_v2.text_diagnostics import CORRUPTION_TYPES, apply_corruption


@pytest.mark.parametrize("kind", CORRUPTION_TYPES)
def test_corruption_is_deterministic(kind):
    text = "Sinh viên không đăng nhập được tài khoản 192.168.1.1, mã 2026."
    first = apply_corruption(text, kind, 2, 42)
    second = apply_corruption(text, kind, 2, 42)
    assert first == second


def test_all_corruptions_apply_to_rich_fixture():
    text = "Sinh viên không đăng nhập được tài khoản 192.168.1.1, mã 2026."
    for kind in CORRUPTION_TYPES:
        result = apply_corruption(text, kind, 3, 9)
        assert result.applied, kind
        assert result.text != text
        assert result.metadata["controlled_injection_only"] is True


def test_invalid_severity_is_rejected():
    with pytest.raises(ValueError, match="severity"):
        apply_corruption("xin chào", "word_deletion", 0, 1)


def test_empty_source_is_explicitly_excluded():
    result = apply_corruption("", "word_insertion", 1, 1)
    assert result.applied is False
    assert result.exclusion_reason == "empty_source_text"


def test_missing_ip_is_explicitly_excluded():
    result = apply_corruption("không có địa chỉ", "ip_address_corruption", 1, 1)
    assert result.applied is False
    assert result.exclusion_reason == "no_applicable_source_pattern"


def test_generator_dry_run_is_complete_and_does_not_write(tmp_path):
    source = tmp_path / "source.jsonl"
    source.write_text(
        json.dumps(
            {
                "audio_id": 1,
                "reference_transcript": "Lỗi mạng tại 192.168.1.1 mã 2026.",
                "split": "dev",
                "intent": "network",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "config.json"
    manifest = tmp_path / "manifest.jsonl"
    config = {
        "schema_version": "1.0.0",
        "seed": 10,
        "source_manifest": str(source),
        "severities": [1, 2, 3],
        "corruptions": list(CORRUPTION_TYPES),
        "outputs": {
            "manifest": str(manifest),
            "summary": str(tmp_path / "summary.json"),
            "metadata": str(tmp_path / "metadata.json"),
        },
        "disclosure": "controlled diagnostic",
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")
    summary = generate(config, config_path, dry_run=True)
    assert summary["planned_rows"] == 30
    assert summary["writes_performed"] is False
    assert not manifest.exists()

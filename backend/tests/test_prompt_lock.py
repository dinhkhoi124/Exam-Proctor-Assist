import pytest

from dataset_benchmark.scripts.common import resolve_path, sha256_file
from dataset_benchmark.scripts.run_benchmark import validate_prompt_lock


def test_test_split_requires_the_exact_locked_prompt_hash():
    current = sha256_file(resolve_path("backend/app/prompts/asr_correction.py"))
    validate_prompt_lock(
        {"prompt_lock": {"status": "locked", "sha256": current}}, "test"
    )

    with pytest.raises(RuntimeError, match="changed after lock"):
        validate_prompt_lock(
            {"prompt_lock": {"status": "locked", "sha256": "wrong"}}, "test"
        )


def test_dev_split_does_not_require_a_prompt_lock():
    validate_prompt_lock({}, "dev")

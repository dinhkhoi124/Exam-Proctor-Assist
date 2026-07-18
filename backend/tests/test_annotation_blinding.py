import random

from dataset_benchmark.scripts.annotations import balanced_swap_flags


def test_blind_order_is_randomized_reproducible_and_balanced():
    first = balanced_swap_flags(60, random.Random(43))
    second = balanced_swap_flags(60, random.Random(43))

    assert first == second
    assert sum(first) == 30
    assert first != sorted(first)

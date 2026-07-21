"""Controlled text-corruption diagnostics, separate from audio robustness."""

from .corruptions import CORRUPTION_TYPES, CorruptionResult, apply_corruption

__all__ = ["CORRUPTION_TYPES", "CorruptionResult", "apply_corruption"]

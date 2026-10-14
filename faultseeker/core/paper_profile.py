"""Deterministic reentrancy score and tier semantics used by paper mode."""

from __future__ import annotations


STORAGE_WEIGHTS = {
    "repeated_slot_nested": 0.55,
    "write_after_external_call": 0.25,
    "same_function_reentered": 0.20,
    "write_before_and_after": 0.10,
    "same_slot_rewritten": 0.10,
}
STRUCTURAL_WEIGHTS = {
    "same_function_reentered": 0.45,
    "same_contract_different_selector": 0.35,
    "nested_depth_reentry": 0.35,
}
STRUCTURAL_PENALTY = 0.75
STRUCTURAL_CAP = 0.80
PAPER_DETECTION_THRESHOLD = 0.30


def score_reentrancy(evidence: dict[str, bool], fallback: bool) -> float:
    weights = STRUCTURAL_WEIGHTS if fallback else STORAGE_WEIGHTS
    score = sum(weight for signal, weight in weights.items() if evidence.get(signal, False))
    if fallback:
        score = min(score * STRUCTURAL_PENALTY, STRUCTURAL_CAP)
    return round(min(score, 1.0), 4)


def reentrancy_tier(score: float) -> str:
    if score >= 0.80:
        return "CONFIRMED_REENTRANCY"
    if score >= 0.55:
        return "HIGH_RISK_REENTRANCY"
    if score >= 0.30:
        return "POSSIBLE_REENTRANCY"
    if score >= 0.10:
        return "UNLIKELY_REENTRANCY"
    return "NOT_REENTRANCY"

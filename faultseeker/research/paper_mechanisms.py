"""Opt-in implementation-paper audit metadata.

The implementation paper describes both executable mechanisms and empirical
claims.  This module records the former without treating a capability
declaration as evidence that a provider, dataset, or historical experiment
was actually available.  It is intentionally read-only and is not imported by
the normal analysis pipeline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


VALID_STATUSES = frozenset({"EXISTS", "PARTIAL", "MISSING"})


@dataclass(frozen=True)
class MechanismRecord:
    mechanism: str
    paper_location: str
    status: str
    repository_paths: tuple[str, ...]
    scope_note: str

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# The rows are deliberately mechanism-level.  Numeric outcomes, benchmark
# authenticity, and literature assertions are not implementation mechanisms.
PAPER_MECHANISMS: tuple[MechanismRecord, ...] = (
    MechanismRecord("dual-path explorer/RPC collection", "III-A, Algorithm 1", "EXISTS",
                    ("faultseeker/utils/explorer_provider.py", "faultseeker/utils/rpc_provider.py",
                     "faultseeker/data_collection/txn_replayer.py"),
                    "Explorer and scored RPC fallback are implemented; live endpoint success is a separate claim."),
    MechanismRecord("explorer EMA ranking and circuit breaker", "III-A", "EXISTS",
                    ("faultseeker/utils/explorer_provider.py",),
                    "EMA alpha, endpoint scoring, and half-open recovery are executable and locally testable."),
    MechanismRecord("RPC weighted failover, LRU/TTL cache, and batch calls", "III-A", "EXISTS",
                    ("faultseeker/utils/rpc_provider.py",),
                    "Defaults are 512 entries and 600 seconds; no provider availability is implied."),
    MechanismRecord("Foundry replay with call/gas/selector/storage observations", "III-A", "PARTIAL",
                    ("faultseeker/data_collection/txn_replayer.py", "faultseeker/data_collection/storage_trace.py"),
                    "Foundry and RPC paths exist, but trace/storage completeness depends on the capture and provider."),
    MechanismRecord("zero-LLM five-category deterministic signal extraction", "III-B", "EXISTS",
                    ("faultseeker/forensics/signal_extractor.py",),
                    "Flash loan, price manipulation, access-control observations, reentrancy, and profit signals are emitted."),
     MechanismRecord("EXPLOIT/BENIGN/UNCERTAIN rule classifier", "III-B, Algorithm 1", "EXISTS",
                     ("faultseeker/forensics/rule_classifier.py", "faultseeker/forensics/orchestrator.py"),
                     "Verdict control flow is implemented; population rates are not inferred."),
    MechanismRecord("multi-agent function investigation and ranked candidates", "III-D, Algorithm 1", "EXISTS",
                    ("faultseeker/core/pipeline.py", "faultseeker/function_analysis/function_analyzer.py",
                     "faultseeker/function_analysis/function_ranker.py", "faultseeker/prompts/function_analysis/"),
                    "Specialist prompts, function analysis, and ranking are wired; provider/model quality is separate."),
    MechanismRecord("SSTORE cross-depth storage-mutation reentrancy score", "III-C, Eq. (2)", "EXISTS",
                    ("faultseeker/core/paper_profile.py", "faultseeker/forensics/signal_extractor.py"),
                    "Paper-mode weights and nested-slot evidence are executable."),
    MechanismRecord("structural fallback discount and cap", "III-C", "EXISTS",
                    ("faultseeker/core/paper_profile.py", "faultseeker/forensics/signal_extractor.py"),
                    "Fallback is explicitly marked; capability eligibility is available in the opt-in audit module."),
    MechanismRecord("OpenZeppelin mutex filtering", "III-C", "EXISTS",
                    ("faultseeker/forensics/signal_extractor.py",),
                    "1→2→1 local mutex transitions without nested writes are filtered."),
    MechanismRecord("DELEGATECALL/CALLCODE storage-context normalization", "III-C", "EXISTS",
                    ("faultseeker/forensics/signal_extractor.py", "faultseeker/data_collection/storage_trace.py"),
                    "Storage ownership follows the caller context for delegate-style calls."),
    MechanismRecord("three-tier hybrid LLM routing and local-confidence gate", "III-D", "EXISTS",
                    ("faultseeker/core/llm_router.py", "faultseeker/research/ablation.py"),
                    "Tier selection, Tier-2 fallback, and cloud-only ablation are executable."),
    MechanismRecord("six provider backend adapters", "III-D, III-F", "PARTIAL",
                    ("faultseeker/utils/agent.py", "faultseeker/core/llm_router.py"),
                    "Adapters are declared for Ollama, OpenAI, Gemini, Anthropic, Qwen, and xAI; live conformance is not bundled."),
    MechanismRecord("per-query cost accounting and cloud counterfactual", "III-D, Eq. (3)", "PARTIAL",
                    ("faultseeker/core/llm_router.py", "faultseeker/research/cost_tracker.py",
                     "faultseeker/research/routing_audit.py"),
                    "Token/provider usage is tracked when supplied; estimated and observed usage are now separated opt-in."),
    MechanismRecord("four-factor confidence scoring", "III-E, Eq. (4)", "EXISTS",
                    ("faultseeker/core/confidence_scorer.py",),
                    "PMS/CES/TCS/LCS weights and interpretability levels are implemented as relative heuristics."),
    MechanismRecord("structured evidence cards", "III-E", "PARTIAL",
                    ("faultseeker/core/confidence_scorer.py", "faultseeker/core/pipeline.py",
                     "faultseeker/research/evidence_provenance.py"),
                    "Cards exist; provenance is optional and must be attached explicitly for claim-grade evidence."),
    MechanismRecord("two HITL checkpoints and five guidance types", "III-E", "EXISTS",
                    ("faultseeker/core/human_interface.py", "faultseeker/core/pipeline.py"),
                    "CLI checkpoints and structured modifications are implemented; no human-study outcome is asserted."),
    MechanismRecord("JSON forensic report and optional benchmark row", "III-A, Fig. 2", "EXISTS",
                    ("faultseeker/forensics/result.py", "faultseeker/main.py", "benchmark/run_eval.py"),
                    "Serialization and evaluation row construction exist."),
     MechanismRecord("multi-chain EVM coverage", "III-A, IV-A", "PARTIAL",
                     ("faultseeker/utils/rpc_provider.py", "faultseeker/utils/explorer_provider.py",
                      "faultseeker/research/chain_profiles.py"),
                     "Chain registries exist, while the paper's ten-chain authenticated cohort is not established."),
    MechanismRecord("curated annotated multi-chain benchmark", "I, IV-A", "PARTIAL",
                    ("benchmark/", "benchmark/evidence_manifest.py", "benchmark/research_protocol.py",
                     "benchmark/versions/"),
                    "Dataset import, validation, split, and provenance tooling exist; the paper's 246-row authenticated cohort is not present."),
    MechanismRecord("trace capability and storage eligibility metadata", "III-A/III-C", "MISSING",
                    ("faultseeker/research/trace_capability.py",),
                    "Added opt-in decisions distinguish storage-backed, structural-fallback, and ineligible observations."),
    MechanismRecord("artifact/evidence provenance for evidence cards", "III-E, III-F", "MISSING",
                    ("faultseeker/research/evidence_provenance.py",),
                    "Added opt-in digest-bound observed/derived/synthetic evidence ledger."),
    MechanismRecord("adversarial versus empirical/synthetic evaluation separation", "V, IV", "MISSING",
                    ("faultseeker/research/evaluation_partition.py", "faultseeker/research/adversarial.py"),
                    "Added opt-in partition guard so perturbations cannot silently enter empirical metrics."),
    MechanismRecord("empirical calibration with disjoint provenance", "III-E, VI", "PARTIAL",
                    ("faultseeker/research/calibration.py",),
                    "A dependency-free calibrator exists and enforces disjoint IDs; calibrated production outcomes remain opt-in."),
)


def mechanism_matrix() -> list[dict[str, Any]]:
    """Return a JSON-serializable copy of the audit matrix."""
    return [record.to_dict() for record in PAPER_MECHANISMS]


def records_with_status(status: str) -> tuple[MechanismRecord, ...]:
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
    return tuple(record for record in PAPER_MECHANISMS if record.status == status)


def render_markdown(records: Iterable[MechanismRecord] = PAPER_MECHANISMS) -> str:
    """Render the matrix for a review artifact without embedding paper numbers."""
    lines = [
        "# Implementation-paper feature matrix",
        "",
        "Status describes repository mechanisms, not empirical validity or reported numbers.",
        "",
        "| Mechanism | Paper location | Status | Exact repository paths | Scope note |",
        "|---|---|---|---|---|",
    ]
    for record in records:
        paths = "<br>".join(f"`{path}`" for path in record.repository_paths)
        note = record.scope_note.replace("|", "\\|")
        lines.append(f"| {record.mechanism} | {record.paper_location} | **{record.status}** | {paths} | {note} |")
    return "\n".join(lines) + "\n"

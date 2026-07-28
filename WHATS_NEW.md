# What changed in this build

All changes are additive except four targeted fixes. Nothing in `faultseeker/`
core logic was rewritten, so your existing behaviour is intact.

## Verified in this sandbox

```
PASSED=88  FAILED=0  SKIPPED(fixtures)=13  MODULE_ERRORS=5
```

The 5 module errors are only this sandbox missing `ollama` and `networkx`
(both are in `requirements.txt`, so they will import on your machine).
Run `python run_tests_nopytest.py` for a dependency-free check, or
`python -m pytest tests -q` normally.

**Note:** the reentrancy test failure I reported earlier was my own test-runner
shim doing exact float comparison instead of `pytest.approx`. Your code was
correct. Fixed.

## New: leakage-free evaluation (`benchmark/honest_eval/`)

| File | Purpose |
|---|---|
| `leakage_guard.py` | `GuardedFeatures` raises `LeakageError` if a scorer reads `label`, `vuln_type`, `pool_status`, etc. Makes the old bug impossible, not just discouraged. |
| `metrics.py` | Precision/recall/F1/FPR, pooled bootstrap CI (1,000 resamples), Brier (Eq. 7), ECE (Eq. 8), reliability table, McNemar. |
| `features.py` | Dataset loading plus `audit_feature_coverage()` which detects the exploit/benign feature-availability imbalance. |
| `localization.py` | Parses real `location` targets from ground truth; Top-k accuracy and MRR. |

## New entry points

```bash
# Leakage-free classification eval (currently exits 2: blocked, by design)
python benchmark/run_honest_experiments.py

# Real fault-localization eval on 115 ground-truth transactions
python benchmark/run_localization_eval.py --predictions-dir data/output

# Collect benign trace features (needs an archive RPC) - unblocks Tables 4 and 5
python benchmark/collect_benign_traces.py --limit 1000 --rpc-url $ETH_RPC_URL
```

## New instrumentation

- `faultseeker/research/cost_tracker.py` - real per-stage timing and per-tier
  token/USD cost, with a measured all-cloud counterfactual. Replaces the
  unbacked S6.7 numbers.
- `faultseeker/research/ablation.py` - `AblationConfig` with real
  `--disable-faegl/--disable-tig/--disable-calibration/--disable-llm-routing/
  --disable-adversarial-hardening` switches, so ablations bypass code paths
  instead of subtracting a constant.

## Fixes

1. `run_tests_nopytest.py` - proper `pytest.approx` tolerance in the shim.
2. `benchmark/research_readiness_report.py` - UTF-8 BOM bug fixed. The CSV's
   first column key was `\ufeffk"txn_hash"`, so `row.get("txn_hash")` returned
   `None` and `unique_transactions` reported **0**. Now reports **231**.
3. `requirements.txt` - added `pytest>=7.4.0`.
4. `.github/workflows/ci.yml` - CI runs the suite so the test count can never
   drift from the paper again.

## Quarantined

`reports/research_results/` moved to `reports/SYNTHETIC_DO_NOT_CITE/` with a
README explaining exactly why each number is invalid.
`benchmark/run_research_experiments.py` now prints a warning banner on every run
and is marked deprecated in its docstring.

## Read this first

`PAPER_CLAIM_AUDIT.md` maps every claim in the paper to
IMPLEMENTED / MEASURABLE / BLOCKED / UNSUPPORTED, with the exact command to
produce each number.

## Still yours to do

- Rotate the live QuickNode key in `foundry.toml` (public in your repo now).
- Run the benign trace collector with your own RPC key.
- Verify the 16.7-hour figure against reference [5].

---

## Update 2: ablation + cost tracking wired into the real pipeline

In the first pass, `AblationConfig` and `CostTracker` existed and were unit-tested
but were imported by **nothing except their own tests**. They are now on the real
execution path.

### Files changed

**`faultseeker/forensics/adaptive_controller.py`**
- `AdaptiveFailureAwareController(localizer=None, ablation=None)`.
- When `faegl` is disabled the controller returns immediately and **never calls
  the localizer**, so the empty-candidate-set recovery genuinely does not happen.
  Returns `algorithm_decision = {"ablated": True, "component": "faegl"}`.

**`faultseeker/forensics/orchestrator.py`**
- `ForensicsOrchestrator(..., ablation=None, cost_tracker=None)`; the ablation
  config is propagated into the adaptive controller.
- `--disable-tig`: the interaction graph is **not constructed at all**
  (`graph_reasoning = {"ablated": True, "component": "tig"}`), so the dependent
  features `call_depth_max` and `token_flow_anomaly` fall to their defaults.
  This is a behavioural ablation, not a score adjustment.
- New `_stage(name)` wraps each stage in `cost_tracker.stage(...)` when a tracker
  is attached, else `contextlib.nullcontext()` — zero overhead when unused.
  Currently instrumented: `stage1_signal_extraction`, `stage1_interaction_graph`.
- New `_calibrated_confidence(features)` puts calibration (paper section 5.3) on
  the real scoring path. It writes `signals.raw["calibrated_confidence"]` and
  `signals.raw["ablation"]`.

### Calibration is opt-in by design

`_calibrated_confidence` returns `None` unless **both** hold:
1. `ablation.enabled("calibration")` is true, and
2. `FAULTSEEKER_CALIBRATOR_PATH` points to a trained calibrator JSON.

An untrained deployment therefore reports **no probability** rather than a
fabricated one. Train and save via `LogisticConfidenceCalibrator.fit(...).save(path)`.
The calibrator is fed `trace_entropy`, `call_depth`, `token_flow_anomaly`, and
`state_delta`; the remaining four `FEATURE_NAMES` (`pattern_match`,
`code_evidence`, `txn_consistency`, `llm_confidence`) default to 0.0 and should be
supplied from the Stage-2 agent output before you report calibration numbers.

### Tests

`tests/test_orchestrator_wiring.py` — 11 tests:
- FAEGL enabled by default; disabled path is a real no-op; disabled path bypasses
  the localizer (verified with a localizer that raises if called); enabled path
  provably calls both `decide` and `rank_candidates`.
- Orchestrator accepts and propagates the ablation config; defaults to full
  system with no tracker; `_stage` records timing with a tracker and is safe
  without one; calibration returns `None` when untrained and when ablated.

The six orchestrator-level tests `pytest.skip` when `ollama`/`networkx`/`tqdm`
are absent. They were verified to **pass** (not skip) against throwaway stub
modules, and will run for real once you `pip install -r requirements.txt`.

### Usage

```python
from faultseeker.research.ablation import AblationConfig
from faultseeker.research.cost_tracker import CostTracker
from faultseeker.forensics.orchestrator import ForensicsOrchestrator

tracker = CostTracker()
orch = ForensicsOrchestrator(
    ablation=AblationConfig.disabling("tig"),   # or .full_system()
    cost_tracker=tracker,
)
# ... run over your corpus ...
tracker.write_report("reports/honest_results/cost_report.json")
```

Environment-variable form (for sweeps):
```bash
FAULTSEEKER_DISABLE_TIG=1 python your_runner.py
```
via `AblationConfig.from_env(os.environ)`.

### Still not wired

- `llm_routing` and `adversarial_hardening` are declared in `COMPONENTS` and
  respected by `AblationConfig`, but the orchestrator does not yet consult them.
  Their call sites are in `faultseeker/core/llm_router.py` and the prompt-
  construction path, which need a live model to verify — do this locally.
- `record_llm_call` is not yet invoked from `llm_router.py`, so cost numbers will
  show stage latencies but zero token cost until you add that one call.

---

## Update 3: LLM routing + cost bridge wired; adversarial hardening finding

### `faultseeker/core/llm_router.py`

- `HybridLLMRouter(..., ablation=None, cost_tracker=None)`.
- **`--disable-llm-routing` now works.** `select_model()` returns the cloud model
  for every query, bypassing the tier heuristic entirely. Verified: with routing
  enabled a tier-1 query selects `llama3:8b`; disabled, the same query selects
  `gpt-4o-mini`.
- **`record_llm_call` is now actually called.** `record_query()` forwards each
  query into the `CostTracker` with stage, tier (`local`/`cloud`), model, token
  estimates, and latency. Section 6.7 numbers can now be measured.
- `record_query()` gained an optional trailing `agent_role=''` used as the cost
  stage label; existing callers are unaffected.

### `faultseeker/forensics/orchestrator.py`

- The orchestrator now propagates its `ablation` and `cost_tracker` into the
  router it was given, so a single CLI flag reaches the real query path.

### Finding: there is no adversarial hardening to ablate

`AblationConfig` still declares `adversarial_hardening`, but I did not wire it,
because **the component does not exist in the pipeline.**

`faultseeker/research/adversarial.py` contains `AdversarialRobustnessEvaluator`,
which only *generates* perturbations (misleading function names, proxy
obfuscation, recursive noise, fake events, prompt-injection calldata) and
measures score deltas. It is imported only by `tests/` and by the deprecated
`benchmark/run_research_experiments.py`. There is no sanitiser, no prompt-
injection defence, and no hardening step anywhere on the analysis path.

So the paper's "−adversarial hardening" ablation row has nothing to remove, and
the old `0.9673` value for it was constant subtraction. **Either implement a real
defence, or drop that row and reframe section 6.5 as a robustness probe of the
unhardened system** — which is what the evaluator actually measures, and is still
a legitimate result.

### Verified test counts

| Environment | Result |
|---|---|
| No optional deps | 93 passed, 0 failed, 29 skipped, 122 collected, 5 module errors |
| All imports satisfied | **115 passed, 0 failed, 14 skipped, 129 collected, 0 module errors** |

The second row was produced against throwaway stub modules for
`networkx`/`ollama`/`tqdm`/`openai`, which are **not** in this archive. It proves
the wiring is structurally correct; it does not prove runtime behaviour under the
real libraries. Reproduce with `pip install -r requirements.txt && pytest tests -q`.

### Ablation variants you can now legitimately run

| Variant | Status |
|---|---|
| `full_system` | Real |
| `minus_faegl` | Real — localizer bypassed |
| `minus_tig` | Real — graph never constructed |
| `minus_calibration` | Real — calibrator never consulted |
| `minus_llm_routing` | Real — all queries forced to cloud |
| `minus_adversarial_hardening` | **Do not report** — nothing implemented to disable |

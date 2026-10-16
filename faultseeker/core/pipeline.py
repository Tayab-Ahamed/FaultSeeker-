import os
import json
import time
import re
import math
from copy import deepcopy
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from faultseeker.core.config import FaultSeekerConfig
from faultseeker.core.confidence_scorer import ConfidenceScorer, generate_evidence_card
from faultseeker.core.human_interface import HumanInterface, AnalystFeedback
from faultseeker.core.llm_router import HybridLLMRouter
from faultseeker.forensics.result import (
    extract_reentrancy_analysis,
    compute_priority_breakdown,
)
from faultseeker.research.calibration import LogisticConfidenceCalibrator, production_features


class FaultSeekerPipeline:

    def __init__(self, config: FaultSeekerConfig, *, forensics_orchestrator=None,
                 function_ranker=None, function_analyzer=None, human_interface=None):
        """
        Initialize the FaultSeeker pipeline.

        Args:
            config: FaultSeeker configuration object
        """
        self.config = config
        self.forensics_orchestrator = forensics_orchestrator
        self.function_ranker = function_ranker
        self.function_analyzer = function_analyzer
        self.human_interface = human_interface
        self.router = None
        self._agents_initialized = False

    @staticmethod
    def _parse_txn_link(txn_link: str) -> Tuple[str, str]:
        # Extract transaction hash (0x followed by 64 hex characters)
        pattern = r'(0x[0-9a-fA-F]{64})'
        matches = re.findall(pattern, txn_link)
        if not matches:
            raise ValueError(f"Could not extract transaction hash from link: {txn_link}")
        txn_hash = matches[0]

        # Determine chain from URL (Gap 5: Multi-Chain — expanded from 2 to 8 chains)
        txn_link_lower = txn_link.lower()
        chain_map = [
            ('bscscan', 'bsc'),
            ('bsc', 'bsc'),
            ('polygonscan', 'polygon'),
            ('polygon', 'polygon'),
            ('arbiscan', 'arbitrum'),
            ('arbitrum', 'arbitrum'),
            ('optimistic.etherscan', 'optimism'),
            ('optimism', 'optimism'),
            ('snowtrace', 'avalanche'),
            ('avalanche', 'avalanche'),
            ('basescan', 'base'),
            ('base', 'base'),
            ('ftmscan', 'fantom'),
            ('fantom', 'fantom'),
            # Gap 3 fix: add zksync and gnosis (benchmark chains 9 & 10)
            ('explorer.zksync', 'zksync'),
            ('zksync', 'zksync'),
            ('gnosisscan', 'gnosis'),
            ('gnosis', 'gnosis'),
            ('etherscan', 'eth'),
            ('eth', 'eth'),
        ]
        chain = None
        for keyword, chain_id in chain_map:
            if keyword in txn_link_lower:
                chain = chain_id
                break
        if not chain:
            raise ValueError(f"The blockchain network is not supported: {txn_link}")

        return txn_hash, chain

    def _initialize_forensics(self):
        if self.forensics_orchestrator is None:
            from faultseeker.forensics.orchestrator import ForensicsOrchestrator
            self.forensics_orchestrator = ForensicsOrchestrator(
                model=self.config.forensics_model,
                cache_dir=self.config.get_forensics_cache_dir(),
            )

    def _initialize_stage2_agents(self):
        if self._agents_initialized:
            return

        # Gap 1+6: Build router if auto_route is enabled
        if self.function_analyzer is None and getattr(self.config, 'auto_route', False):
            # Use the dedicated cloud_model if set; fall back to function_analysis_model
            router_cloud = (getattr(self.config, 'cloud_model', '') or
                            self.config.function_analysis_model or
                            self.config.forensics_model)
            self.router = HybridLLMRouter(
                local_model=getattr(self.config, 'local_model', 'llama3:8b'),
                cloud_model=router_cloud,
                confidence_gate=getattr(self.config, 'confidence_gate', 0.6),
                track_cost=getattr(self.config, 'track_cost', False),
                routing_strategy=getattr(self.config, 'routing_strategy', 'hybrid'),
            )

        from faultseeker.function_analysis.function_ranker import FunctionRanker
        from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer

        if self.function_ranker is None:
            print("   [+] Initializing function ranker...")
            self.function_ranker = FunctionRanker()

        if self.function_analyzer is None:
            print("   [+] Initializing function analyzer...")
            self.function_analyzer = FunctionAnalyzer(
                model=self.config.function_analysis_model,
                router=self.router,
            )

        self._agents_initialized = True

    def _initialize_agents(self):
        """Compatibility entry point for callers explicitly setting up all stages."""
        self._initialize_forensics()
        self._initialize_stage2_agents()

    @staticmethod
    def _load_calibrator(path):
        calibrator = LogisticConfidenceCalibrator.load(path)
        calibrator.require_schema('production-confidence-v1')
        return calibrator

    def _attach_transaction_cost(self, result, baseline):
        """Isolate this call's append-only router observations from batch history."""
        cumulative=deepcopy(self.router.get_cost_summary()) if self.router else {}
        prior=baseline.get('records',[])
        records=cumulative.get('records',[])
        if len(records)<len(prior) or records[:len(prior)]!=prior:
            raise ValueError('Router accounting history changed during transaction')
        current=deepcopy(cumulative)
        current['records']=deepcopy(records[len(prior):])
        for name in ('total_queries','local_queries','cloud_queries','fallback_count',
                     'total_cost_usd','estimated_cloud_only_cost'):
            if name not in cumulative:
                continue
            before,after=baseline.get(name,0),cumulative[name]
            if (type(before) not in (int,float) or type(after) not in (int,float)
                    or not math.isfinite(before) or not math.isfinite(after)
                    or before<0 or after<before):
                raise ValueError('Invalid router accounting delta')
            current[name]=after-before
        current['accounting_scope']='this transaction only; appended router observations'
        if 'estimated_cloud_only_cost' in current:
            estimated=current['estimated_cloud_only_cost']
            savings=estimated-current.get('total_cost_usd',0)
            current['savings_usd']=savings
            current['savings_percent']=round(100*savings/estimated,1) if estimated else 0.0
            current['savings_scope']='modeled cloud-only counterfactual; not measured savings'
        result['llm_cost']=float(current.get('total_cost_usd',0))
        result['query_records']=deepcopy(current['records'])
        if self.router and getattr(self.config,'track_cost',False):
            result['cost_summary']=current
            cumulative['accounting_scope']='router lifetime cumulative; do not sum across transaction reports'
            result['router_cumulative_cost_summary']=cumulative
        return result

    def analyze_transaction(self,
                          txn_link: Optional[str] = None,
                          txn_hash: Optional[str] = None,
                          chain: Optional[str] = None,
                          analyst_guidance: Optional[Dict[str, Any]] = None,
                          analysis_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze a transaction and identify vulnerabilities.

        Args:
            txn_link: Transaction link (e.g., https://etherscan.io/tx/0x...)
            txn_hash: Transaction hash (alternative to txn_link)
            chain: Blockchain identifier (required if txn_hash is provided)

        Returns:
            Dictionary containing forensics and function analysis results

        Raises:
            ValueError: If input parameters are invalid
            RuntimeError: If analysis stages fail
        """
        start_time = time.time()
        cost_baseline=deepcopy(self.router.get_cost_summary()) if self.router else {}

        # Validate and parse input
        if not txn_link and not (txn_hash and chain):
            raise ValueError("Either txn_link or (txn_hash and chain) must be provided")

        # Parse txn_link if provided
        if txn_link:
            txn_hash, chain = self._parse_txn_link(txn_link)

        # Stage 1 runs before any Stage 2 model or router is constructed.
        self._initialize_forensics()

        print("\n[Stage 1] Transaction-Level Forensics")
        print("   [+] Fetching transaction data from blockchain...")

        # Stage 1: Transaction-Level Forensics
        if analysis_context is None:
            forensics_result, txn_seq, txn_info = self.forensics_orchestrator.run(txn_hash, chain)
        else:
            forensics_result, txn_seq, txn_info = self.forensics_orchestrator.run(
                txn_hash, chain, analysis_context=analysis_context)

        if not forensics_result:
            raise RuntimeError("Stage 1 (Forensics) failed to produce results")

        print("   [OK] Forensics analysis completed")

        # Gap 8: Med-B - Trace Visualization (Visualizes trace tree and call types)
        try:
            import matplotlib.pyplot as plt
            viz_dir = getattr(self.config, 'output_dir', './data/output')
            os.makedirs(viz_dir, exist_ok=True)
            viz_path = os.path.join(viz_dir, f"{txn_hash}_trace.png")
            self.forensics_orchestrator.txn_sequencer.save_visualization(viz_path)
            plt.close('all')
            print(f"   [OK] Trace visualization saved to {viz_path}")
        except Exception as e:
            print(f"   [!] Note: Could not generate trace visualization: {str(e)}")

        # Gap 2: HITL Checkpoint 1 — Post-Forensics
        hitl = self.human_interface or HumanInterface(enabled=getattr(self.config, 'human_in_loop', False))
        hitl_feedback_1 = hitl.checkpoint_post_forensics(forensics_result)
        if analyst_guidance:
            hitl_feedback_1 = AnalystFeedback(
                checkpoint='post_forensics', action='modify',
                modifications=analyst_guidance,
                notes='Structured analyst guidance supplied to pipeline',
            )
            hitl.feedback_log.append(hitl_feedback_1)
        if hitl_feedback_1.action == 'modify':
            hitl.apply_post_forensics(forensics_result, hitl_feedback_1)
            print("   [Analyst] Analyst modifications recorded")

        rule_verdict = getattr(forensics_result, 'rule_verdict', 'UNCERTAIN')
        rule_confidence = float(getattr(forensics_result, 'rule_confidence', 0.0) or 0.0)
        reclassification_locked = rule_verdict == 'EXPLOIT' and rule_confidence >= 0.85
        if (rule_verdict == 'BENIGN' and rule_confidence >= 0.85
                and self.config.enable_benign_prefilter):
            signals = getattr(forensics_result, 'signals', {}) or {}
            priority = compute_priority_breakdown(signals, exploitability_score=0.0)
            bypass_result = {
                'transaction_hash': forensics_result.transaction_hash,
                'chain': forensics_result.chain,
                'verdict': 'BENIGN', 'rule_verdict': rule_verdict,
                'rule_confidence': rule_confidence,
                'matched_rule': getattr(forensics_result, 'matched_rule', ''),
                'stage2_bypassed': True, 'reclassification_locked': False,
                'ranked_suspicious_functions': [],
                'potentially_vulnerable_functions': [],
                'scored_functions': [], 'evidence_cards': [],
                'rejected_findings': [], 'finding_count': 0,
                'transaction_understanding': 'Deterministic clean-coverage rule',
                'reentrancy': extract_reentrancy_analysis(signals),
                'priority': priority, 'priority_score': priority['total'],
                'analyst_feedback': hitl.get_feedback_log(),
                'analysis_context': analysis_context or {},
                'llm_cost': 0.0, 'query_records': [],
                'signals': signals,
                'duration': time.time() - start_time,
                'timestamp': datetime.now().isoformat(),
            }

            return self._attach_transaction_cost(bypass_result,cost_baseline)

        self._initialize_stage2_agents()

        print("\n[Stage 2] Task-Driven Function Analysis")
        print("   [+] Ranking suspicious functions...")

        # Stage 2a: Function Ranking (fast, deterministic)
        tx_analysis = {
            'transaction_hash': forensics_result.transaction_hash,
            'chain': forensics_result.chain,
            'trace': forensics_result.trace,
            'repeated_patterns': forensics_result.repeated_patterns,
            'function_call_loc_memo': forensics_result.function_call_loc_memo
        }
        ranking_result = self.function_ranker.rank(forensics_result, tx_analysis)

        print(f"   [OK] Ranking completed - {len(ranking_result.address_list)} addresses to analyze")
        print("   [+] Analyzing vulnerable functions...")

        # Stage 2b: In-Depth Function Analysis (LLM-driven, uses ranking output)
        analysis_result = self.function_analyzer.run(forensics_result, txn_seq, txn_info, ranking_result)

        if not analysis_result:
            raise RuntimeError("Stage 2 (Function Analysis) failed to produce results")

        candidates = analysis_result.get('potentially_vulnerable_functions', [])
        if isinstance(candidates, dict):
            normalized = []
            for identity, details in candidates.items():
                function, separator, address = identity.rpartition('_')
                if not separator or not isinstance(details, dict):
                    raise ValueError('Malformed function-analysis finding identity')
                normalized.append(dict(details, function=function, address=address))
            analysis_result['potentially_vulnerable_functions'] = normalized

        print("   [OK] Function analysis completed")

        # Equation 4 is a relative ranking. An explicitly selected, compatible
        # calibrator may replace it; no published empirical rate is implied.
        finalized_functions = analysis_result.get('finalized_vulnerable_functions', [])
        scored_functions = []
        evidence_cards = []
        if finalized_functions:
            print("\n[Stage 3] Confidence Scoring")
            scorer = ConfidenceScorer()
            forensics_data = {
                'repeated_patterns': forensics_result.repeated_patterns if hasattr(forensics_result, 'repeated_patterns') else [],
                'balance_change': forensics_result.balance_change if hasattr(forensics_result, 'balance_change') else {},
                'potential_attacker': forensics_result.potential_attacker if hasattr(forensics_result, 'potential_attacker') else [],
                'potential_victim': forensics_result.potential_victim if hasattr(forensics_result, 'potential_victim') else [],
            }
            scored_functions = scorer.score_all(finalized_functions, forensics_data)

            # Paper §5.3: replace proxy score with logistic calibrator when model present
            calibration_path = getattr(self.config, 'calibration_model_path', '')

            if calibration_path:
                    calibrator = self._load_calibrator(calibration_path)
                    print(f"   [OK] Logistic calibrator loaded from {calibration_path}")
                    for sf in scored_functions:
                        # Build the 8-feature vector expected by the calibrator
                        conf = sf.get('confidence', {})
                        comps = conf.get('components', {}) if isinstance(conf, dict) else {}
                        stage1_signals = getattr(forensics_result, 'signals', {}) or {}
                        row = production_features(comps,stage1_signals)
                        calibrated_prob = calibrator.predict_proba(row)
                        # Update the confidence dict with calibrated score
                        if isinstance(sf.get('confidence'), dict):
                            sf['confidence']['overall'] = round(calibrated_prob, 4)
                            sf['confidence']['level'] = scorer._classify(calibrated_prob)
                            sf['confidence']['score_type'] = 'calibrated_probability'
                            sf['confidence']['score_semantics'] = 'calibrated-probability'
                            sf['confidence']['calibrated'] = True
                            sf['confidence']['calibration_model'] = calibration_path
                        else:
                            sf['confidence'] = {
                                'overall': round(calibrated_prob, 4),
                                'level': scorer._classify(calibrated_prob),
                                'score_type': 'calibrated_probability',
                                'calibrated': True,
                                'calibration_model': calibration_path,
                            }
                    # Re-sort by calibrated score
                    scored_functions.sort(key=lambda x: x.get('confidence', {}).get('overall', 0.0), reverse=True)
                    print(f"   [OK] Calibrated {len(scored_functions)} functions (logistic calibrator, paper §5.3)")
            else:
                print(f"   [OK] Scored {len(scored_functions)} functions (4-factor heuristic; no calibrator model found)")

        # Gap 2: HITL Checkpoint 2 — Vulnerability Review (after scoring)
        hitl_feedback_2 = hitl.checkpoint_vulnerability_review(scored_functions)
        scored_functions, rejected_findings = hitl.apply_vulnerability_review(
            scored_functions, hitl_feedback_2)
        if rejected_findings:
            rejected_keys = {(item['function'], item['address']) for item in rejected_findings}
            analysis_result['potentially_vulnerable_functions'] = [
                item for item in analysis_result.get('potentially_vulnerable_functions', [])
                if (item.get('function', ''), item.get('address', '')) not in rejected_keys
            ]
        for sf in scored_functions:
            card = generate_evidence_card(sf, sf.get('confidence', {}))
            if hitl_feedback_2.action == 'modify':
                card['analyst_notes'] = sf.get('analyst_notes') or hitl_feedback_2.modifications.get('analyst_notes', '')
                if sf.get('analyst_confirmed'):
                    card['analyst_confirmed'] = True
            evidence_cards.append(card)

        # Build clean final output with only essential results
        reentrancy = extract_reentrancy_analysis(getattr(forensics_result, 'signals', {}))
        priority = compute_priority_breakdown(
            getattr(forensics_result, 'signals', {}),
            exploitability_score=getattr(forensics_result, 'rule_confidence', 0.0),
        )
        result = {
            'transaction_hash': forensics_result.transaction_hash,
            'chain': forensics_result.chain,
            'verdict': rule_verdict,
            'rule_verdict': rule_verdict,
            'rule_confidence': rule_confidence,
            'matched_rule': getattr(forensics_result, 'matched_rule', ''),
            'stage2_bypassed': False,
            'analysis_complete': analysis_result.get('analysis_complete',True),
            'analysis_errors': analysis_result.get('analysis_errors',[]),
            'reclassification_locked': reclassification_locked,

            # Main analysis results
            'ranked_suspicious_functions': analysis_result.get('ranked_result', []),
            'potentially_vulnerable_functions': analysis_result.get('potentially_vulnerable_functions', []),
            'transaction_understanding': analysis_result.get('transaction_understanding', ''),

            # Gap 3+4: Confidence scores and evidence cards
            'scored_functions': scored_functions,
            'signals': getattr(forensics_result,'signals',{}),
            'evidence_cards': evidence_cards,
            'rejected_findings': rejected_findings,
            'finding_count': len(scored_functions),
            'reentrancy': reentrancy,
            'priority': priority,
            'priority_score': priority['total'],

            # Gap 2: Analyst feedback log
            'analyst_feedback': hitl.get_feedback_log(),
            'analysis_context': analysis_context or {},

            # Metadata
            'duration': time.time() - start_time,
            'timestamp': datetime.now().isoformat(),

            # Optional: Store full results for debugging
            '_debug': {
                'forensics_duration': forensics_result.duration,
                'analysis_duration': analysis_result.get('duration'),
                'functions_to_inspect_count': forensics_result.get_function_count()
            }
        }

        # Keep each transaction's observed calls separate from shared-router
        # history. The cumulative batch view is explicitly named in the result.
        return self._attach_transaction_cost(result,cost_baseline)

    def save_results(self, result: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Save analysis results to file.

        Args:
            result: Analysis results to save
            output_path: Optional custom output path. If None, generates timestamped path.

        Returns:
            Path where results were saved
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.config.output_dir, f"analysis_{timestamp}.json")

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Save results
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

        return output_path

    def analyze_and_save(self,
                        txn_link: Optional[str] = None,
                        txn_hash: Optional[str] = None,
                        chain: Optional[str] = None,
                        output_path: Optional[str] = None) -> str:
        """
        Convenience method to run analysis and save results in one call.

        Args:
            txn_link: Transaction link
            txn_hash: Transaction hash
            chain: Blockchain identifier
            output_path: Optional output file path

        Returns:
            Path where results were saved
        """
        result = self.analyze_transaction(txn_link, txn_hash, chain)
        saved_path = self.save_results(result, output_path)
        return saved_path

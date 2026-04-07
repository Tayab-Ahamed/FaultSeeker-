import os
import json
import argparse
from datetime import datetime
from faultseeker.core.config import FaultSeekerConfig
from faultseeker.core.pipeline import FaultSeekerPipeline
from faultseeker.core.auto_model_selector import (
    auto_select_models, print_model_selection, interactive_model_selection
)


def banner():
    print("\n" + "="*60)
    print("🔍 FaultSeeker - Blockchain Transaction Analyzer")
    print("="*60)



def main(txn_link: str = None,
         txn_hash: str = None,
         chain: str = None,
         forensics_model: str = None,
         function_analysis_model: str = None,
         cache_dir: str = './data/cache',
         output_dir: str = './data/output',
         explain: bool = False):


    banner()
    print("\n📋 Transaction Information:")
    if txn_link:
        print(f"   • Link: {txn_link}")
    elif txn_hash and chain:
        print(f"   • Hash: {txn_hash}")
        print(f"   • Chain: {chain.upper()}")
    else:
        raise ValueError("Either txn_link or both txn_hash and chain must be provided.")

    # ── Auto-detect models when not explicitly provided ────────────────
    auto_route = False
    local_model_name = None
    cloud_model_name = None

    if not forensics_model or not function_analysis_model:
        # Show interactive menu: lists all detected local + cloud options
        model_config = interactive_model_selection()
        print_model_selection(model_config)

        local_model_name  = model_config.get('local_model')
        actual_cloud      = model_config.get('actual_cloud_model')  # real cloud API model

        if model_config.get('use_hybrid') and actual_cloud:
            # Hybrid: Stage 1 (data collection) → local, Stage 2 (analysis) → cloud
            forensics_model         = forensics_model         or local_model_name
            function_analysis_model = function_analysis_model or actual_cloud
            cloud_model_name        = actual_cloud
            auto_route = True
            print(f"   🔀 Hybrid mode: Stage 1 → {forensics_model} (local), Stage 2 → {function_analysis_model} (cloud)")
        else:
            # Single model for everything (either only local or only cloud)
            single = model_config['cloud_model']
            forensics_model         = forensics_model         or single
            function_analysis_model = function_analysis_model or single

    # Display configuration
    print("\n⚙️  Configuration:")
    print(f"   • Forensics Model: {forensics_model}")
    print(f"   • Function Analysis Model: {function_analysis_model}")
    if auto_route:
        print(f"   • Routing: Hybrid (local Tier 1/2, cloud Tier 3)")


    # Set output path and cache root
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"analysis_{timestamp}.json")

    print(f"   • Cache Directory: {cache_dir}")
    print(f"   • Output Directory: {output_dir}")

    # Create and run pipeline
    print("\n🚀 Initializing analysis pipeline...")
    pipeline = FaultSeekerPipeline(
        config=FaultSeekerConfig(
            forensics_model=forensics_model,
            function_analysis_model=function_analysis_model,
            cloud_model=cloud_model_name or '',   # actual cloud API model for Tier 3
            cache_dir=cache_dir,
            auto_route=auto_route,
            local_model=local_model_name or forensics_model,
            routing_strategy='hybrid',
        )
    )
    print("   ✓ Pipeline initialized successfully")

    result = pipeline.analyze_transaction(
        txn_link=txn_link,
        txn_hash=txn_hash,
        chain=chain
    )

    # Save results
    print("\n💾 Saving analysis results...")
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"   ✓ Results saved to: {output_path}")

    # Print RPC provider scoreboard (observability)
    try:
        from faultseeker.utils.rpc_provider import print_provider_stats
        from faultseeker.utils.explorer_provider import print_explorer_stats
        print_provider_stats(chain)
        print_explorer_stats(chain)
    except Exception:
        pass


    # Display evidence cards if --explain is set (Gap 3: Explainability)
    if explain and result.get('evidence_cards'):
        print(f"\n📋 Evidence Cards ({len(result['evidence_cards'])} findings):")
        print("-" * 60)
        for i, card in enumerate(result['evidence_cards'], 1):
            sig = card.get('function_signature', {})
            conf = card.get('confidence', {})
            print(f"\n  [{i}] {sig.get('function', '?')} @ {sig.get('address', '?')[:10]}...")
            print(f"      Confidence: {conf.get('overall', 0):.1%} ({conf.get('level', '?')})")
            components = conf.get('components', {})
            if components:
                print(f"      ├─ Pattern Match:   {components.get('pattern_match', 0):.1%}")
                print(f"      ├─ Code Evidence:   {components.get('code_evidence', 0):.1%}")
                print(f"      ├─ Txn Consistency: {components.get('txn_consistency', 0):.1%}")
                print(f"      └─ LLM Confidence:  {components.get('llm_confidence', 0):.1%}")
            evidence = card.get('evidence', [])
            if evidence:
                print("      Evidence:")
                for ev in evidence[:3]:
                    print(f"        • {str(ev)[:80]}")
        print("-" * 60)

    print("\n✅ Analysis completed successfully!")
    print("="*60 + "\n")

    return result


def run_analysis(txn_hash: str, chain: str,
                 model: str = 'gpt-4o-mini',
                 local_model: str = None,
                 cache_dir: str = './data/cache',
                 output_dir: str = './data/output',
                 explain: bool = False) -> dict:
    """
    Importable entry point for programmatic use (eval scripts, cross-chain runner).
    Returns the raw analysis result dict.
    """
    forensics_model = local_model if local_model else model
    function_analysis_model = model
    return main(
        txn_hash=txn_hash,
        chain=chain,
        forensics_model=forensics_model,
        function_analysis_model=function_analysis_model,
        cache_dir=cache_dir,
        output_dir=output_dir,
        explain=explain,
    )


def main_cli():

    parser = argparse.ArgumentParser(
        description="FaultSeeker: LLM-Empowered Framework for Blockchain Transaction Forensics",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Input arguments
    parser.add_argument(
        "-txn_link",
        help="Transaction link to analyze (e.g., https://etherscan.io/tx/0x...)"
    )
    parser.add_argument(
        "-txn_hash",
        help="Transaction hash to analyze (alternative to txn_link)"
    )
    parser.add_argument(
        "-chain",
        default="eth",
        help="Chain identifier (eth, bsc, poly, opt, arbi, avax, fantom, base)"
    )

    # Model arguments
    parser.add_argument(
        "-forensics_model",
        default=None,
        help="Model for Stage 1 forensics analysis (default: auto-detect)"
    )
    parser.add_argument(
        "-function_analysis_model",
        default=None,
        help="Model for Stage 2 function analysis (default: auto-detect)"
    )

    # Output arguments
    parser.add_argument(
        "-output",
        default="./data/output",
        help="Output file path for analysis results (default: ./data/output/analysis_YYYYMMDD_HHMMSS.json)"
    )
    parser.add_argument(
        "-cache",
        default="./data/cache",
        help="Cache directory for intermediate results (default: ./data/cache)"
    )

    # Gap 3+4: Explainability flags
    parser.add_argument(
        "--explain",
        action="store_true",
        default=False,
        help="Display detailed evidence cards with confidence scores (Gap 3+4)"
    )

    # Gap 1+6: Hybrid LLM routing flags
    parser.add_argument(
        "--auto-route",
        action="store_true",
        default=False,
        help="Enable hybrid LLM routing between local and cloud models (Gap 1)"
    )
    parser.add_argument(
        "--track-cost",
        action="store_true",
        default=False,
        help="Track and display LLM API costs (Gap 6)"
    )
    parser.add_argument(
        "--local-model",
        default="llama3:8b",
        help="Local model for Ollama when using --auto-route (default: llama3:8b)"
    )

    # Gap 2: Human-in-the-Loop
    parser.add_argument(
        "--human-in-loop",
        action="store_true",
        default=False,
        help="Enable analyst interaction at key checkpoints (Gap 2)"
    )

    args = parser.parse_args()

    # Validate input
    if not args.txn_link and not (args.txn_hash and args.chain):
        parser.error("Either -txn_link or both -txn_hash and -chain must be provided")

    # Run main
    try:
        main(
            txn_link=args.txn_link,
            txn_hash=args.txn_hash,
            chain=args.chain,
            forensics_model=args.forensics_model,
            function_analysis_model=args.function_analysis_model,
            cache_dir=args.cache,
            output_dir=args.output,
            explain=args.explain,
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main_cli()

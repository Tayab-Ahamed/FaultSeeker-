import os
import re
import subprocess


# Map short chain names to ARCHIVE-capable RPC URLs
# (cast run requires debug_traceTransaction — standard nodes do NOT support this)
CHAIN_RPC_MAP = {
    'eth':       'https://rpc.ankr.com/eth',
    'ethereum':  'https://rpc.ankr.com/eth',
    # BSC: QuikNode archive (primary) with Alchemy as fallback
    'bsc':       'https://restless-thrilling-darkness.bsc.quiknode.pro/5b30b0da70126411f777c3c8d9730d1998fc7922/',
    'bnb':       'https://restless-thrilling-darkness.bsc.quiknode.pro/5b30b0da70126411f777c3c8d9730d1998fc7922/',
    'polygon':   'https://rpc.ankr.com/polygon',
    'poly':      'https://rpc.ankr.com/polygon',
    'arbitrum':  'https://rpc.ankr.com/arbitrum',
    'arb':       'https://rpc.ankr.com/arbitrum',
    'optimism':  'https://rpc.ankr.com/optimism',
    'op':        'https://rpc.ankr.com/optimism',
    'avalanche': 'https://rpc.ankr.com/avalanche',
    'avax':      'https://rpc.ankr.com/avalanche',
    'base':      'https://rpc.ankr.com/base',
    'fantom':    'https://rpc.ankr.com/fantom',
    'ftm':       'https://rpc.ankr.com/fantom',
}

# Fallback RPCs tried if the primary fails
CHAIN_RPC_FALLBACK = {
    'bsc': 'https://bnb-mainnet.g.alchemy.com/v2/Jw4UMI_aOIJ_qL7-pJSjV',
    'bnb': 'https://bnb-mainnet.g.alchemy.com/v2/Jw4UMI_aOIJ_qL7-pJSjV',
}


class TransactionReplayer:

    def __init__(self, cache_path='./data/cache/replay'):
        """Initialize TransactionReplayer with cache directory."""
        self.cache_path = cache_path
        os.makedirs(cache_path, exist_ok=True)

    @staticmethod
    def _resolve_rpc(chain: str) -> str:
        """Resolve chain short name to RPC URL. Passthrough if already a URL."""
        if chain.startswith('http'):
            return chain
        return CHAIN_RPC_MAP.get(chain.lower(), chain)

    @staticmethod
    def _run_cast(txn_hash, rpc_url):
        """Run cast run with a given RPC URL. Returns clean stdout or None."""
        command = ["cast", "run", "--quick", txn_hash, '--rpc-url', rpc_url]
        print(' '.join(command))
        try:
            result = subprocess.run(command, capture_output=True, timeout=7200)
            ansi_escape = re.compile(rb'\x1b\[[0-9;]*[a-zA-Z]')
            clean_bytes = ansi_escape.sub(b'', result.stdout)
            clean = clean_bytes.decode('utf-8', errors='ignore')
            if not clean.strip():
                err = ansi_escape.sub(b'', result.stderr).decode('utf-8', errors='ignore').strip()
                if err:
                    print(f"      ✗ cast stderr: {err}")
                return None
            return clean
        except Exception:
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def transaction_replay(txn_hash, chain):
        """Execute transaction replay using cast command, with fallback RPC."""
        primary_rpc = TransactionReplayer._resolve_rpc(chain)
        result = TransactionReplayer._run_cast(txn_hash, primary_rpc)
        if result:
            return result

        # Try fallback RPC if primary failed
        chain_key = chain.lower() if not chain.startswith('http') else None
        if chain_key and chain_key in CHAIN_RPC_FALLBACK:
            fallback_rpc = CHAIN_RPC_FALLBACK[chain_key]
            print(f"      ↻ Primary RPC failed, trying fallback: {fallback_rpc}")
            result = TransactionReplayer._run_cast(txn_hash, fallback_rpc)

        return result

    def get_replay_cache(self, txn_hash):
        """Check if replay result exists in cache."""
        cache_file = os.path.join(self.cache_path, txn_hash.lower() + '.txt')
        if os.path.exists(cache_file):
            return open(cache_file, 'r', encoding='utf-8', errors='ignore').read()
        return None

    def cache_replay(self, txn_hash, invocation_flow):
        """Cache replay result to disk."""
        with open(os.path.join(self.cache_path, txn_hash.lower() + '.txt'), 'w', encoding='utf-8') as f:
            f.write(invocation_flow)

    def run(self, txn_hash: str, chain: str) -> str:
        """
        Run transaction replay for given transaction hash and chain.

        Args:
            txn_hash: Transaction hash
            chain: Chain identifier (eth, bsc, poly, etc.)

        Returns:
            Transaction replay trace text
        """
        # Check cache first
        invocation_flow = self.get_replay_cache(txn_hash)
        if invocation_flow:
            # Reject previously cached rate-limit / Cloudflare error pages
            if '<html' in invocation_flow.lower() or 'cloudflare' in invocation_flow.lower():
                print(f"      ⚠ Stale/invalid cache detected for {txn_hash[:10]}... — clearing")
                import os
                bad = os.path.join(self.cache_path, txn_hash.lower() + '.txt')
                try:
                    os.remove(bad)
                except OSError:
                    pass
                invocation_flow = None
            else:
                return invocation_flow

        # Run replay and cache only valid results
        invocation_flow = self.transaction_replay(txn_hash, chain)
        if invocation_flow:
            # Guard: do not cache error pages from rate-limited / blocked RPCs
            if '<html' in invocation_flow.lower() or 'cloudflare' in invocation_flow.lower():
                print("      ✗ RPC returned an error page (rate-limited?). Not caching.")
                return None
            self.cache_replay(txn_hash, invocation_flow)

        return invocation_flow




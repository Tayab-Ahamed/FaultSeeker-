import json
from faultseeker.data_collection.txn_replayer import TransactionReplayer
from faultseeker.data_collection.trace_parser import TraceParser, TraceNode
from faultseeker.data_collection.trace_visualizer import TraceGraphGenerator, TransactionTraceVisualizer


class TransactionSequencer:
    def __init__(self):
        self.replayer = TransactionReplayer()
        self.parser = TraceParser()
        self.generator = TraceGraphGenerator()
        self.visualizer = TransactionTraceVisualizer()
    
    def analyze_trace(self, trace_text, depth_limit=1000):
        root_node = self.parser.parse(trace_text,depth_limit)
        if root_node:
            self.visualizer.build_graph_from_tree(root_node)
        return root_node.to_dict() if root_node else None

    @staticmethod
    def _canonical_to_legacy_trace(node: dict) -> dict:
        """Convert canonical RPC trace nodes into the legacy parser-like schema."""
        if not node:
            return {}

        return {
            'type': 'create' if node.get('call_type') in {'CREATE', 'CREATE2'} else 'call',
            'gas': node.get('gas'),
            'address': node.get('callee'),
            'function': node.get('function_selector'),
            'params': node.get('input', '0x')[10:] if node.get('input') else '',
            'call_type': (node.get('call_type') or '').lower() or None,
            'value': node.get('value'),
            'contract_type': None,
            'children': [
                TransactionSequencer._canonical_to_legacy_trace(child)
                for child in node.get('children', [])
            ],
        }
    
    def generate_text_representation(self, root_node):
        return self.generator.generate(root_node)
    
    def visualize_trace(self, figsize=(12, 10)):
        return self.visualizer.draw_graph(figsize=figsize)
    
    def visualize_address_relation(self):
        return self.visualizer.draw_address_relation()
    
    def save_visualization(self, filename="transaction_trace_graph.png"):
        self.visualizer.save_graph(filename)
    
    def display_gas_summary(self):
        self.visualizer.display_gas_summary()
    
    def export_to_json(self, root_node, filename="transaction_trace.json"):
        if isinstance(root_node, TraceNode):
            root_node = root_node.to_dict()
            
        with open(filename, 'w') as f:
            json.dump(root_node, f, indent=2)
    
    def from_structured(self, structured):
        """Process an observed canonical trace with the same production metadata.

        This path performs no I/O. The caller establishes capture provenance;
        missing coverage flags are retained, never promoted by conversion.
        """
        if not isinstance(structured.get('trace'), dict) or not structured.get('transaction_hash') or not structured.get('chain'):
            raise ValueError('Canonical transaction, chain and trace required')
        root = structured['trace']
        legacy = self._canonical_to_legacy_trace(root)
        self.visualizer.build_graph_from_tree(TraceNode.from_dict(legacy))
        self.parser.address_call_memo = {}
        self.parser.created_address = []

        def visit(node):
            address = (node.get('callee') or '').lower()
            if address:
                if node.get('call_type') in {'CREATE', 'CREATE2'}:
                    if address not in self.parser.created_address:
                        self.parser.created_address.append(address)
                else:
                    functions = self.parser.address_call_memo.setdefault(address, [])
                    selector = node.get('function_selector') or '0x'
                    if selector not in functions:
                        functions.append(selector)
            for child in node.get('children', []):
                visit(child)
        visit(root)
        return {
            'transaction_hash': structured['transaction_hash'], 'chain': structured['chain'],
            'trace': legacy, 'canonical_trace': root,
            'storage_events': structured.get('storage_events', []),
            'storage_reads': structured.get('storage_reads', []),
            'trace_state_diff': structured.get('state_diff', {}),
            'trace_coverage': dict(structured.get('trace_coverage') or {}),
            'address_relation': self.visualize_address_relation(),
            'address_calls': self.parser.address_call_memo,
            'created_address': self.parser.created_address,
        }

    def run(self, txn_hash: str, chain: str) -> dict:
        """
        Analyze transaction sequence for given transaction hash and chain.

        Args:
            txn_hash: Transaction hash
            chain: Chain identifier (eth, bsc, poly, etc.)

        Returns:
            Dictionary containing transaction sequence analysis results
        """
        # Prefer the structured trace path for canonical call/state metadata.
        structured_trace = self.replayer.get_structured_trace(txn_hash, chain)

        # Get cast-style trace text from replayer (uses cache internally)
        trace_text = self.replayer.run(txn_hash, chain)
        if not trace_text and not structured_trace:
            return {}

        # Analyze trace
        root_node = self.analyze_trace(trace_text) if trace_text else None
        if not root_node and structured_trace and structured_trace.get('trace'):
            return self.from_structured(structured_trace)
        if not root_node:
            return {}

        # Build result
        address_relation = self.visualize_address_relation()
        result = {
            "transaction_hash": txn_hash,
            "chain": chain,
            "trace": root_node,
            "canonical_trace": structured_trace.get('trace') if structured_trace else None,
            "storage_events": structured_trace.get('storage_events', []) if structured_trace else [],
            "storage_reads": structured_trace.get('storage_reads', []) if structured_trace else [],
            "trace_state_diff": structured_trace.get('state_diff', {}) if structured_trace else {},
            "trace_coverage": structured_trace.get('trace_coverage', {
                'trace_complete': False,
                'token_flow_complete': False,
                'multi_tx_context_complete': False,
            }) if structured_trace else {
                'trace_complete': False,
                'token_flow_complete': False,
                'multi_tx_context_complete': False,
            },
            "address_relation": address_relation,
            "address_calls": self.parser.address_call_memo,
            "created_address": self.parser.created_address,
        }

        return result


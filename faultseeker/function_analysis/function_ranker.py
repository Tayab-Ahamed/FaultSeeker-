from copy import deepcopy
import json
from dataclasses import dataclass, field
import re
from typing import Dict, List


@dataclass
class RankingResult:
    repeated_patterns: List[Dict] = field(default_factory=list)
    address_calls_with_created_contract_in_params: Dict[str, Dict] = field(default_factory=dict)
    functions_to_be_inspected: Dict[str, Dict] = field(default_factory=dict)
    address_list: List[str] = field(default_factory=list)
    ranked_functions: List[Dict] = field(default_factory=list)


_CALL_ANNOTATION = re.compile(r"\s*\{[^{}]*\}\s*$")


def canonical_call_label(value: str) -> str:
    """Remove renderer-only call annotations while preserving ABI syntax."""
    return _CALL_ANNOTATION.sub("", str(value or "")).strip()


def _depth_measure(calls: list[dict]) -> int:
    depths = [call.get("depth") for call in calls]
    return max((len(depth) for depth in depths if isinstance(depth, (list, tuple))), default=0)


def _prediction_depth_measure(prediction: dict) -> int:
    return max(
        (len(depth) for depth in prediction.get("supporting_call_depths", [])
         if isinstance(depth, (list, tuple))),
        default=0,
    )


def _path_concentration(count: int, depths: list[object]) -> float:
    """Measure repeated observations per distinct caller path.

    A depth path's final element identifies the observed call; removing that
    element leaves the caller path.  Repeated calls from one caller path are
    stronger ordering evidence than the same number of calls spread across
    many unrelated paths.  The count remains a later tie-breaker so this
    feature cannot erase the underlying observation volume entirely.
    """
    parent_paths = {
        tuple(depth[:-1])
        for depth in depths
        if isinstance(depth, (list, tuple)) and depth
    }
    return float(count) / max(1, len(parent_paths))


def _prediction_path_concentration(prediction: dict) -> float:
    depths = list(prediction.get("supporting_call_depths") or [])
    return _path_concentration(int(prediction.get("count") or 0), depths)


def _terminal_fanout(depths: list[object]) -> int:
    """Count distinct terminal call positions in supporting depth paths."""
    return len({
        depth[-1]
        for depth in depths
        if isinstance(depth, (list, tuple)) and depth
    })


def _prediction_terminal_fanout(prediction: dict) -> int:
    return _terminal_fanout(list(prediction.get("supporting_call_depths") or []))


def _candidate_path_concentration(candidate: dict) -> float:
    calls = list(candidate.get("calls") or [])
    depths = [call.get("depth") for call in calls if isinstance(call, dict)]
    return _path_concentration(int(candidate.get("count") or 0), depths)


def _candidate_terminal_fanout(candidate: dict) -> int:
    calls = list(candidate.get("calls") or [])
    depths = [call.get("depth") for call in calls if isinstance(call, dict)]
    return _terminal_fanout(depths)


_RANK_TIE_POLICY = (
    "call-path concentration desc; terminal fanout asc; max depth desc; count desc; "
    "stable candidate encounter order"
)


def rerank_saved_predictions(predictions: List[Dict]) -> List[Dict]:
    """Apply the production label/grouping and depth tie rules offline.

    This adapter is deliberately limited to already-produced candidates. It
    cannot create evidence absent from a saved trace and is used only for the
    frozen offline comparison.
    """
    grouped = {}
    encounter = 0
    for prediction in predictions:
        item = deepcopy(prediction)
        address = str(item.get("code_address") or item.get("address") or "").lower()
        raw_function = item.get("function_name") or item.get("function") or ""
        function = canonical_call_label(raw_function)
        key = (address, function)
        if key not in grouped:
            item["code_address"] = address
            item["function_name"] = function
            item["_encounter"] = encounter
            item["_max_depth"] = _prediction_depth_measure(item)
            item["_path_concentration"] = _prediction_path_concentration(item)
            item["_terminal_fanout"] = _prediction_terminal_fanout(item)
            item["count"] = int(item.get("count") or 0)
            item["supporting_call_depths"] = list(item.get("supporting_call_depths") or [])
            grouped[key] = item
            encounter += 1
        else:
            current = grouped[key]
            current["count"] += int(item.get("count") or 0)
            for depth in list(item.get("supporting_call_depths") or []):
                if depth not in current["supporting_call_depths"]:
                    current["supporting_call_depths"].append(depth)
            current["_max_depth"] = max(current["_max_depth"], _prediction_depth_measure(item))
            current["_path_concentration"] = _prediction_path_concentration(current)
            current["_terminal_fanout"] = _prediction_terminal_fanout(current)
    ordered = sorted(
        grouped.values(),
        key=lambda item: (
            -item["_path_concentration"],
            item["_terminal_fanout"],
            -item["_max_depth"],
            -item["count"],
            item["_encounter"],
        ),
    )
    output = []
    for rank, item in enumerate(ordered, start=1):
        item["rank"] = rank
        item["tie_policy"] = _RANK_TIE_POLICY
        item.pop("_encounter", None)
        item.pop("_max_depth", None)
        item["path_concentration"] = _prediction_path_concentration(item)
        item["terminal_fanout"] = _prediction_terminal_fanout(item)
        output.append(item)
    return output


class FunctionRanker:
    def __init__(self):
        """Initialize the function ranker."""
        # Read-only functions and standard safe state-changing functions to filter out
        # (not typically vulnerable, focus analysis on custom functions)
        self.filtered_functions = [
            # ERC20 read-only
            'totalsupply', 'balanceof', 'allowance', 'decimals', 'name', 'symbol',
            # ERC721 read-only
            'ownerof', 'tokenuri', 'getapproved', 'isapprovedforall',
            # Uniswap/DEX read-only
            'token0', 'token1', 'getreserves', 'getamountout', 'getamountin',
            'getamountsout', 'getamountsin', 'factory', 'pair', 'getpair',
            # Other common read-only
            'paused', 'owner', 'admin', 'ispaused', 'totalshares', 'pricepershare',
            # Standard state-changing (usually safe)
            'transfer', 'transferfrom', 'approve',
            # Common swap variants (routing functions, usually safe)
            'swapexacttokensfortokenssupportingfeeontransfertokens',
            'swapexacttokensfortokens', 'swapexacttokensfornative',
            'swapexacttokensfornativetokens', 'swapnativetokensfortokens',
            'swapnativetokensfortokenswithfeeontransfertokens'
        ]

        # Extended filter for created contract analysis
        # Include additional Aave/protocol-specific safe functions
        self.extended_filtered_functions = self.filtered_functions + [
            # Aave-specific safe functions
            'transferunderlyingto', 'transferfromunderlying',
            'approveunderlying', 'allowanceunderlying',
            # Additional swap variants
            'swapnativetokensfortokenswithfeeontransfertokenssupportingfeeontransfertokens',
            'algebraswapcallback'
        ]

    def rank(self, forensics_result, tx_analysis: dict) -> RankingResult:
        """
        Rank functions for detailed analysis.

        Args:
            forensics_result: ForensicsResult from Stage 1
            tx_analysis: Prepared transaction analysis data

        Returns:
            RankingResult containing ranked functions and patterns
        """
        address_list = []
        functions_to_be_inspected = {}
        address_calls_with_created_contract_in_params = {}
        address_calls_with_created_contract_in_params_memo = {}
        function_call_memo = {}
        repeated_patterns = []

        # Process repeated patterns
        repeated_patterns_memo = []
        for _, value in tx_analysis['repeated_patterns'].items():
            for pattern in value:
                if (len(pattern['pattern']) > 1) or (pattern['repeats']) > 3:
                    if len(pattern['pattern']) == 1:
                        if pattern['pattern'][0]['call_type'] == 'staticcall':
                            continue

                    # Check if pattern contains only filtered functions
                    check = sum([1 for i in pattern['pattern']
                               if (i['function'] is None) or
                               (canonical_call_label(i['function']).lower() in self.filtered_functions)])

                    if check == 0:
                        # Deduplicate only identical evidence records. Different
                        # owners, call order, depths or repeat counts are distinct
                        # observations and must survive for downstream analysis.
                        repeated_memo_key = json.dumps(pattern, sort_keys=True)
                        if repeated_memo_key not in repeated_patterns_memo:
                            repeated_patterns_memo.append(repeated_memo_key)
                            repeated_patterns.append(deepcopy(pattern))

        # Process calls with created contracts in params
        for call in forensics_result.address_calls_with_created_contract:
            function_label = canonical_call_label(call['function'])
            if function_label.lower() in self.extended_filtered_functions:
                continue

            key = function_label
            if key not in address_calls_with_created_contract_in_params:
                address_calls_with_created_contract_in_params[key] = {
                    'count': 0,
                    'calls': [],
                    'address': [],
                }
                address_calls_with_created_contract_in_params_memo[key] = []

            if call['address'] not in address_list:
                address_list.append(call['address'])

            if str(call['depth']) not in address_calls_with_created_contract_in_params_memo[key]:
                address_calls_with_created_contract_in_params_memo[key].append(str(call['depth']))
                address_calls_with_created_contract_in_params[key]['count'] += 1
                address_calls_with_created_contract_in_params[key]['calls'].append({
                    'gas': call['gas'],
                    'address': call['address'],
                    'params': call['params'] if len(call['params']) < 200 else f"{call['params'][:200]}...",
                    'depth': call['depth']
                })
                if call['address'] not in address_calls_with_created_contract_in_params[key]['address']:
                    address_calls_with_created_contract_in_params[key]['address'].append(call['address'])

        # Process functions to be inspected
        for _, value in forensics_result.functions_to_be_inspected.items():
            if value:
                for call in value:
                    function_label = canonical_call_label(call['function'])
                    if function_label.lower() in self.extended_filtered_functions:
                        continue

                    key = function_label + '_' + call['address']
                    if key not in functions_to_be_inspected:
                        functions_to_be_inspected[key] = {
                            'count': 0,
                            'calls': []
                        }
                        function_call_memo[key] = []

                    if call['address'] not in address_list:
                        address_list.append(call['address'])

                    if str(call['depth']) not in function_call_memo[key]:
                        function_call_memo[key].append(str(call['depth']))
                        functions_to_be_inspected[key]['count'] += 1
                        functions_to_be_inspected[key]['calls'].append({
                            'gas': call['gas'],
                            'params': call['params'] if len(call['params']) < 200 else f"{call['params'][:200]}...",
                            'depth': call['depth']
                        })

        # Fallback: if no functions found, use function_call_loc_memo
        if len(functions_to_be_inspected) == 0:
            for function_call in tx_analysis['function_call_loc_memo']:
                raw_function, address = function_call.rsplit('::', 1)
                function_call_key = canonical_call_label(raw_function) + '_' + address
                function_call_value = {
                    'count': len(tx_analysis['function_call_loc_memo'][function_call]),
                    'calls': [
                        {
                            'gas': call['gas'],
                            'params': call['params'],
                            'depth': call['depth']
                        }
                        for call in tx_analysis['function_call_loc_memo'][function_call]
                    ]
                }
                functions_to_be_inspected[function_call_key] = function_call_value

        # Sort functions by repeated observations per distinct caller path,
        # then depth and raw count. This avoids letting broad fan-out wrappers
        # dominate candidates that recur along one exploit-relevant path.
        functions_to_be_inspected = sorted(
            functions_to_be_inspected.items(),
            key=lambda x: (
                -_candidate_path_concentration(x[1]),
                _candidate_terminal_fanout(x[1]),
                -_depth_measure(x[1]['calls']),
                -x[1]['count'],
            ),
        )
        functions_to_be_inspected = {
            k: {'count': v['count'], 'calls': v['calls']}
            for k, v in functions_to_be_inspected
            if v['count'] > 0
        }

        # Export the actual stable count ordering explicitly. Address priority
        # and JSON member ordering are not substitutes for function ranks.
        ranked_functions = []
        for key, candidate in functions_to_be_inspected.items():
            function, address = key.rsplit('_', 1)
            ranked_functions.append({
                'rank': len(ranked_functions) + 1,
                'code_address': address.lower(), 'function': function,
                'selector': function.lower() if (function.startswith('0x') and len(function) == 10) else None,
                'count': candidate['count'],
                'supporting_call_depths': [call['depth'] for call in candidate['calls']],
                'path_concentration': _candidate_path_concentration(candidate),
                'terminal_fanout': _candidate_terminal_fanout(candidate),
                'tie_policy': _RANK_TIE_POLICY,
            })

        return RankingResult(
            repeated_patterns=repeated_patterns,
            address_calls_with_created_contract_in_params=address_calls_with_created_contract_in_params,
            functions_to_be_inspected=functions_to_be_inspected,
            address_list=address_list,
            ranked_functions=ranked_functions
        )

    def get_function_call_depth(self, function_call: str, tx_analysis: dict) -> int:
        """
        Get the maximum call depth for a function.

        Args:
            function_call: Function call identifier (format: "function_address")
            tx_analysis: Transaction analysis data

        Returns:
            Maximum call depth
        """
        temp = function_call.rsplit('_', 1)
        function_name = temp[0].lower()
        address = temp[1].lower()
        key = f"{function_name}::{address}"

        current_depth = 0
        if key in tx_analysis['function_call_loc_memo']:
            for call in tx_analysis['function_call_loc_memo'][key]:
                if len(call['depth']) > current_depth:
                    current_depth = len(call['depth'])

        return current_depth

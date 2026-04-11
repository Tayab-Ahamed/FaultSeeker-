import os
import sys
import json
from faultseeker.data_collection.txn_info_collector import TransactionInfoCollector
from faultseeker.data_collection.contract_info_collector import ContractInfoCollector

TX_HASHES = {
    'eth':       '0xc59f265ec0ee840eda5315c1daa5b4882514fc305470eb76164d3ff762a2c008',
    'bsc':       '0xa287cd352f23aac56d4d795d9f2ae01b5941698d973e8e5a38d2a74f52a0571e',
    'polygon':   '0x9b4d4bb053193f0cc6e567fec6d040f2153e8616fceab12c5956c3c069cbd4be',
    'arbitrum':  '0x17e269822f575a5ada41648b90d860dea2ecc0de98d08d532165976f2a4bf3e8',
    'optimism':  '0x00efc616828a2e374315be70113701e8852782335b12d6da17852d9401f1e33f',
    'avalanche': '0x74abac7e97d36cdcf862387773f2023fa1348dc3450bf04ea8bf5a2d44a810fd',
    'base':      '0x93590bc2b4adda7d4916ad67e27e49c2bc1fcc9f15bdf68e989646d4cdfcbd7b',
    'fantom':    '0xfdc0d62b83c18dc5ac4d10ab552417956a946d954c27da3869b3c18f71b69def',
    'gnosis':    '0x1584ddc240bd250fe8c4ab48f54898b58454607aa902b92dba1f4d8cd4eae6b8',
    'zksync':    '0x95c86ca3702db4c47b725686839099fe18dbac4add5d4528a07015d64dd43019'
}

def test_chain(chain_id, tx_hash):
    print(f"\n{'='*62}")
    print(f"  CHAIN: {chain_id.upper():12} TX: {tx_hash[:20]}...")
    print(f"{'='*62}")

    # Step 1: TransactionInfoCollector
    txn_collector = TransactionInfoCollector()
    txn_result = txn_collector.run(tx_hash, chain_id)

    if not txn_result:
        print(f"  [TXN]  FAIL  Empty result (reverted or network error)")
        return {'txn': 'FAIL', 'contract': 'SKIP', 'source': 'n/a', 'reason': 'collector returned empty'}

    source = txn_result.get('_source', 'html_scrape')
    status = txn_result.get('status', '?')
    addr   = txn_result.get('address_info', {})
    from_a = addr.get('from_address', '')
    to_a   = (addr.get('to_address') or [''])[0]
    print(f"  [TXN]  PASS  Status={status}  Source={source}")
    print(f"         From : {from_a or '(none)'}")
    print(f"         To   : {to_a   or '(none)'}")

    test_address = from_a or to_a
    if not test_address:
        print(f"  [CTRT] SKIP  No address extracted")
        return {'txn': 'PASS', 'contract': 'SKIP', 'source': source, 'reason': 'no address'}

    # Step 2: ContractInfoCollector
    contract_collector = ContractInfoCollector()
    contract_collector.txn_link = txn_collector.txn_link
    contract_result = contract_collector.run(test_address, chain_id)

    if not contract_result:
        print(f"  [CTRT] FAIL  ContractInfoCollector returned empty")
        return {'txn': 'PASS', 'contract': 'FAIL', 'source': source, 'reason': 'contract empty'}

    is_contract = contract_result.get('is_contract', False)
    print(f"  [CTRT] PASS  is_contract={is_contract}  address={test_address[:20]}...")
    return {'txn': 'PASS', 'contract': 'PASS', 'source': source, 'reason': 'ok'}


def main():
    results = {}
    for chain, tx_hash in TX_HASHES.items():
        results[chain] = test_chain(chain, tx_hash)

    print(f"\n\n{'='*62}")
    print(f"  FINAL SUMMARY")
    print(f"{'='*62}")
    print(f"  {'Chain':<12} {'TXN':<8} {'Contract':<12} {'Source':<16} Notes")
    print(f"  {'-'*58}")
    for chain, r in results.items():
        print(f"  {chain:<12} {r['txn']:<8} {r['contract']:<12} {r['source']:<16} {r['reason']}")
    print(f"{'='*62}\n")


if __name__ == '__main__':
    main()

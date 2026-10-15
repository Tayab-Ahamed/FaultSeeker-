"""Offline verified compilation-source bundles for production function analysis.

Only input transport is adapted. Every ABI function receives the full real
compilation source bundle, NOT a purported function slice. No publisher,
expected target, label, or ground-truth annotation enters the returned mapping.
"""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import re
from eth_utils import keccak
from benchmark.research_protocol import identity, load_train, read_bound

ADDRESS = re.compile(r'0x[0-9a-f]{40}\Z')


def _signature(entry):
    def typ(item):
        value=item['type']
        return '('+','.join(typ(c) for c in item['components'])+')'+value[5:] if value.startswith('tuple') else value
    return entry['name']+'('+','.join(typ(i) for i in entry['inputs'])+')'


class VerifiedSourceDownloader:
    """ContractDownloader-compatible, network-free source input adapter.

    Use ``factory`` to bind root, evidence digest and one train transaction.
    Source provenance is separate from the analyzer-facing ``run`` mapping.
    """
    def __init__(self, chain, address, output_dir='./temp2', cache_dir='./data/cache/contracts',
                 *, root, evidence_binding, train_identity):
        self.root=Path(root).resolve()
        self.chain=chain.lower()
        self.address=[address] if isinstance(address,str) else list(address)
        self.address=[a.lower() for a in self.address]
        if any(not ADDRESS.fullmatch(a) for a in self.address):
            raise ValueError('Invalid source address')
        split=json.loads((self.root/'benchmark/eval_split.json').read_text(encoding='utf-8'))
        if train_identity not in split['train_ids'] or not train_identity.startswith(self.chain+':'):
            raise ValueError('Verified source inputs require matching frozen TRAIN membership')
        rows=load_train(split,self.root)
        selected=[r for r in rows if identity(r)==train_identity]
        if len(selected)!=1 or self.chain!='eth':
            raise ValueError('No supported train source identity')
        self.row=selected[0]
        # Consume only input bindings; never retain outcome or publisher fields.
        evidence=json.loads(read_bound(evidence_binding,self.root))
        cases=[c for c in evidence.get('cases',[]) if c.get('identity')==train_identity]
        if len(cases)!=1 or cases[0].get('prestate')!=self.row.get('prestate'):
            raise ValueError('Source historical prestate binding does not match frozen train row')
        self.contracts=[{'address':c['address'].lower(),'response':c['response']}
                        for c in cases[0]['contracts'] if c.get('response')]
        if len({c['address'] for c in self.contracts})!=len(self.contracts):
            raise ValueError('Duplicate cached source identity')
        self.evidence_binding=deepcopy(evidence_binding)
        self.prestate_binding=deepcopy(self.row['prestate'])
        self.txn_hash=self.row['txn_hash']
        self.provenance={}

    @classmethod
    def factory(cls, *, root, evidence_binding, train_identity):
        """Return the production constructor shape with frozen inputs bound."""
        def create(chain,address,output_dir='./temp2',cache_dir='./data/cache/contracts'):
            return cls(chain,address,output_dir,cache_dir,root=root,
                       evidence_binding=evidence_binding,train_identity=train_identity)
        return create

    def run(self):
        raw=read_bound(self.prestate_binding,self.root)
        prestate=json.loads(gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw)
        if prestate.get('transaction_hash')!=self.txn_hash or prestate.get('chain')!=self.chain:
            raise ValueError('Historical prestate transaction identity mismatch')
        codes=prestate['response']['result']
        verified={}
        provenance={}
        # Validate every admitted response, not just the requested addresses.
        for contract in self.contracts:
            address=contract['address']
            data=json.loads(read_bound(contract['response'],self.root))
            historical=codes.get(address,{}).get('code','')
            onchain=data.get('runtimeBytecode',{}).get('onchainBytecode')
            if (not ADDRESS.fullmatch(address) or data.get('address','').lower()!=address
                    or str(data.get('chainId'))!='1' or data.get('runtimeMatch') not in ('exact_match','match')
                    or not isinstance(onchain,str) or len(onchain)<=2
                    or not historical or onchain.lower()!=historical.lower()):
                raise ValueError('Cached source does not verify historical runtime bytecode')
            bundle=[]; source_bindings=[]
            metadata=data.get('metadata') or {}
            if isinstance(metadata,str): metadata=json.loads(metadata)
            for path,record in sorted(data.get('sources',{}).items()):
                content=record.get('content')
                if not isinstance(content,str):
                    raise ValueError('Cached compilation source content unavailable')
                encoded=content.encode('utf-8')
                expected=metadata.get('sources',{}).get(path,{}).get('keccak256')
                if expected and expected.lower()!='0x'+keccak(encoded).hex():
                    raise ValueError('Compiler metadata source digest mismatch')
                bundle.append({'path':path,'content':content})
                source_bindings.append({'path':path,'utf8_sha256':hashlib.sha256(encoded).hexdigest(),
                                        'metadata_keccak256':expected})
            if not bundle or not isinstance(data.get('abi'),list):
                raise ValueError('Verified ABI or compilation source bundle unavailable')
            functions={}
            signatures={}
            for entry in data['abi']:
                if entry.get('type')!='function': continue
                signature=_signature(entry);selector='0x'+keccak(text=signature)[:4].hex()
                # A collision retains the whole bundle and all signature provenance.
                functions[selector]=bundle
                signatures.setdefault(selector,[]).append(signature)
            verified[address]=functions
            provenance[address]={'response':deepcopy(contract['response']),
                'prestate':deepcopy(self.prestate_binding),'evidence':deepcopy(self.evidence_binding),
                'historical_runtime_sha256':hashlib.sha256(bytes.fromhex(historical[2:])).hexdigest(),
                'sources':source_bindings,'abi_signatures':signatures,
                'source_scope':'full_compilation_source_bundle_not_function_slice'}
        self.provenance={a:provenance[a] for a in self.address if a in provenance}
        return {a:deepcopy(verified.get(a,{})) for a in self.address}

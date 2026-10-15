"""Cache narrowly selected public primary sources without executing their code."""
import base64
import hashlib
import json
from pathlib import Path
from urllib.request import Request,urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'reports/claim_closure/sources'


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    fetched, errors, records = [], [], []
    def fetch(url, filename):
        fetched.append(url)
        with urlopen(Request(url,headers={'User-Agent':'FaultSeeker-evidence-acquisition'}),timeout=30) as response:
            data = response.read()
        target = OUTPUT/filename
        target.write_bytes(data)
        return data,target
    publication = {}
    try:
        raw,path = fetch('https://api.github.com/repos/Tayab-Ahamed/FaultSeeker-','public_repository.json')
        metadata = json.loads(raw)
        publication = {'url':metadata['html_url'],'private':metadata['private'],
            'license_spdx':(metadata.get('license') or {}).get('spdx_id'),
            'metadata_artifact':str(path.relative_to(ROOT)).replace('\\','/'),
            'scope':'Public upstream repository availability; current local branch has not been pushed'}
        _,license_path = fetch('https://raw.githubusercontent.com/Tayab-Ahamed/FaultSeeker-/main/LICENSE',
                               'public_repository_LICENSE.txt')
        publication['license_artifact'] = str(license_path.relative_to(ROOT)).replace('\\','/')
    except Exception as error:
        errors.append({'source':'public repository','error_type':type(error).__name__})
    try:
        raw,_ = fetch('https://api.github.com/repos/SunWeb3Sec/DeFiHackLabs/git/trees/main?recursive=1','defihacklabs_tree.json')
        tree = json.loads(raw)
        cases = [('jay','0xd4fafa1261f6e4f9c8543228a67caf9d02811e4ad3058a2714323964a8db61f6'),
                 ('cowswap','0x90b468608fbcc7faef46502b198471311baca3baab49242a4a85b73d4924379b')]
        for name,transaction in cases:
            for item in [x for x in tree['tree'] if x['type']=='blob'
                         and name in Path(x['path']).name.lower() and x['path'].endswith('.sol')][:3]:
                blob,_ = fetch(item['url'],name+'_blob_response.json')
                decoded = base64.b64decode(json.loads(blob)['content'])
                if hashlib.sha1(f'blob {len(decoded)}\0'.encode()+decoded).hexdigest()!=item['sha']:
                    raise ValueError('Git object digest mismatch')
                if transaction.encode() not in decoded:
                    continue
                path = OUTPUT/(name+'_published_poc.sol.txt')
                path.write_bytes(decoded)
                records.append({'file':str(path.relative_to(ROOT)).replace('\\','/'),
                    'url':item['url'],'publisher_id':'SunWeb3Sec-DeFiHackLabs',
                    'transaction_hashes':[transaction],'sha256':hashlib.sha256(decoded).hexdigest(),
                    'git_blob_sha1':item['sha'],'original_repository_path':item['path'],
                    'scope':'Published PoC reference, not an independent reviewer adjudication'})
                break
    except Exception as error:
        errors.append({'source':'published PoC','error_type':type(error).__name__})
    report = {'public_repository':publication,'source_artifacts':records,
              'public_http_fetch_attempts':len(fetched),'requested_public_urls':fetched,
              'errors':errors,'paid_provider_calls':0,'downloaded_code_executed':False}
    (OUTPUT/'acquisition.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({'public_repository_observed':bool(publication),'poc_artifacts':len(records),
                      'public_fetches':len(fetched),'errors':errors}))


if __name__=='__main__':
    main()

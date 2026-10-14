"""Measure explorer challenge recovery from a preregistered URL case list."""
import argparse
import json
import os
import sys
from datetime import datetime,timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from faultseeker.utils.waf_recovery import RecoveryClient,recovery_metrics
from faultseeker.utils.rpc_provider import safe_endpoint_label
from benchmark.evidence_manifest import digest_file


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=Path,default=os.getenv('WAF_CASES_JSON'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--execute-live',action='store_true')
    args = parser.parse_args(argv)
    missing = []
    if not args.cases or not args.cases.is_file():
        missing.append('WAF_CASES_JSON: preregistered real explorer URLs and case IDs')
    if not os.getenv('CURL_IMPERSONATE_BINARY') or not Path(os.environ['CURL_IMPERSONATE_BINARY']).is_file():
        missing.append('CURL_IMPERSONATE_BINARY: browser TLS executable')
    if missing or not args.execute_live:
        report,code = {'status':'PENDING-CREDENTIALS','missing':missing,
                       'execution_requested':args.execute_live,'requests_dispatched':0},2
    else:
        cases = json.loads(args.cases.read_text(encoding='utf-8-sig'))
        if not isinstance(cases,list) or not cases or len(cases)>1000 or len({c['case_id'] for c in cases}) != len(cases):
            raise ValueError('Nonempty unique preregistered cases required; maximum 1000')
        client,results = RecoveryClient(strategies=['standard','browser']),[]
        for case in cases:
            observed = client.fetch(case['url'])
            observed.update(case_id=case['case_id'],endpoint=safe_endpoint_label(case['url']))
            results.append(observed)
        report,code = {'status':'MEASURED','cases_sha256':digest_file(args.cases),
                       'timestamp':datetime.now(timezone.utc).isoformat(),
                       'metrics':recovery_metrics(results),'results':results},0
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f"{report['status']}: {args.output}")
    return code


if __name__ == '__main__':
    raise SystemExit(main())

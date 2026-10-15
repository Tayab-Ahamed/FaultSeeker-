"""Explicitly opted-in gateway smoke checks, separate from paper experiments."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from faultseeker.core.spend_guard import SpendGuard


def assess_response(body, model, nonce):
    valid = False
    try:
        choice = body['choices'][0]
        answer = json.loads(choice['message']['content'])
        usage = body['usage']
        valid = (body['model'] == model and answer == {'nonce': nonce, 'sum': 12}
                 and choice['finish_reason'] == 'stop'
                 and all(type(usage[k]) is int and usage[k] > 0
                         for k in ('prompt_tokens', 'completion_tokens')))
    except (KeyError, ValueError, TypeError, IndexError):
        pass
    return {'status': 'VERIFIED-VIA-NARAROUTER' if valid else 'CONFORMANCE-FAILED',
            'native_adapter_tested': False, 'localization_quality_tested': False,
            'scope': 'Authenticated named gateway alias, structured chat response and reported usage only; upstream vendor identity is not independently attested'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute-live', action='store_true')
    parser.add_argument('--credential-file', type=Path, default=ROOT / '.env')
    parser.add_argument('--gateway', choices=('nara', 'nvidia'), default='nara')
    parser.add_argument('--key-name', choices=('NARAROUTER_API_KEY', 'BYNARA_API_KEY'))
    parser.add_argument('--diagnostic', action='store_true')
    parser.add_argument('--free-control', action='store_true')
    args = parser.parse_args()
    if not args.execute_live:
        raise SystemExit('--execute-live is required')
    from dotenv import dotenv_values
    key_name = 'NVIDIA_API_KEY' if args.gateway == 'nvidia' else (args.key_name or 'NARAROUTER_API_KEY')
    key = os.environ.get(key_name) or dotenv_values(args.credential_file).get(key_name)
    if not key:
        raise SystemExit(key_name + ' is missing')
    out = ROOT / 'reports/provenance_hunt/providers'
    catalog = json.loads((out / 'nara_models.txt').read_text(encoding='utf-8'))['data']
    choices = [('anthropic', 'claude-haiku-5.5'), ('qwen', 'qwen3.8-27b')]
    if args.free_control:
        if args.gateway != 'nara':
            raise SystemExit('Free control is specific to the cached Nara free plan')
        plans = json.loads((out / 'nara_plans.txt').read_text(encoding='utf-8'))['data']
        free_models = next(p['models'] for p in plans if p['code'] == 'free')
        if 'agnes-2.5-flash' not in free_models:
            raise SystemExit('Control is not on the captured free-plan list')
        choices = [('free_control_not_claimed_family', 'agnes-2.5-flash')]
    if args.gateway == 'nvidia':
        # Explicit documented Qwen alias, even if omitted by this key's catalog.
        # A real endpoint attempt distinguishes omission from actual access.
        choices = [('qwen_nvidia', 'qwen/qwen2.5-coder-32b-instruct')]
    # Each tiny request consumes a conservative $0.10 budget allocation, even
    # if a subscription covers it. This is not an observed invoice amount.
    guard = SpendGuard(ROOT / 'data/research/spend_ledger.json',
                       pricing={'nara-conformance-attempt': {'input': 100000, 'output': 0}})
    results = []
    for family, model in choices:
        suffix = '_bynara' if key_name == 'BYNARA_API_KEY' else ''
        if args.diagnostic:
            suffix += '_diagnostic'
        target = out / (family + suffix + '_conformance.json')
        if target.is_file():
            results.append(json.loads(target.read_text(encoding='utf-8')))
            continue
        prices = next((m for m in catalog if m['id'] == model), {})
        if args.gateway == 'nara' and not (0 < prices['input_idr_per_1m'] < 10000 and 0 < prices['output_idr_per_1m'] < 15000):
            raise SystemExit('Catalog pricing outside predeclared tiny-call bounds; refusing dispatch')
        nonce = secrets.token_hex(8)
        payload = {'model': model, 'messages': [
            {'role': 'system', 'content': 'Return only the requested JSON object.'},
            {'role': 'user', 'content': 'Return exactly: ' + json.dumps({'nonce': nonce, 'sum': 7 + 5})}],
            'max_tokens': 128, 'temperature': 0}
        reservation = guard.reserve('nara-conformance-attempt', 1, 0)
        record = {'family': family, 'route': 'https://router.bynara.id/v1/chat/completions',
                  'model_alias': model, 'request': payload, 'catalog_price': prices,
                  'credential_variable': key_name,
                  'budget_allocation_usd': 0.1, 'billing_confirmed': False,
                  'paid_dispatch_attempts': 1}
        if args.gateway == 'nvidia':
            record.update(route='https://integrate.api.nvidia.com/v1/chat/completions',
                alias_source='https://docs.api.nvidia.com/nim/reference/llm-apis',
                scope='One documented Qwen endpoint attempt; trial credits and actual billing not confirmed')
        started = time.perf_counter()
        failed = True
        try:
            request = Request(record['route'], data=json.dumps(payload).encode(), headers={
                'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
            with urlopen(request, timeout=60) as response:
                body = json.load(response)
                record['http_status'] = response.code
            safe = {k: body.get(k) for k in ('id', 'model', 'choices', 'usage', 'provider')}
            if key in json.dumps(safe):
                raise ValueError('Credential echo detected; response not retained')
            record.update(response=safe, **assess_response(body, model, nonce))
            if args.gateway == 'nvidia' and record['status'] == 'VERIFIED-VIA-NARAROUTER':
                record['status'] = 'VERIFIED-VIA-NVIDIA-NIM'
            failed = not record['status'].startswith('VERIFIED-VIA-')
        except HTTPError as error:
            record.update(status='UNVERIFIABLE', http_status=error.code,
                          error_type='HTTPError', native_adapter_tested=False)
            try:
                details = json.loads(error.read(20000)).get('error', {})
                if isinstance(details, dict):
                    record['provider_error'] = {k: str(details[k]).replace(key, '[REDACTED]')[:800]
                        for k in ('type', 'code', 'message') if k in details}
                record['retry_after'] = error.headers.get('Retry-After')
            except (ValueError, TypeError):
                record['provider_error'] = 'Non-JSON error body not retained'
        except Exception as error:
            record.update(status='UNVERIFIABLE', error_type=type(error).__name__, native_adapter_tested=False)
        finally:
            record['duration_seconds'] = time.perf_counter() - started
            guard.settle(reservation, failed=failed)
            target.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        results.append(record)
        print(json.dumps({'family': family, 'status': record['status'], 'http_status': record.get('http_status')}), flush=True)
    report = {'observations': results, 'ollama': 'PENDING-LOCAL-SERVICE',
              'native_anthropic_adapter': 'UNTESTED', 'native_dashscope_adapter': 'UNTESTED',
              'openrouter': 'NOT_USED', 'budget': guard.report()}
    report['budget'].pop('events')
    filename = 'nvidia_conformance.json' if args.gateway == 'nvidia' else 'conformance.json'
    if key_name == 'BYNARA_API_KEY':
        filename = 'bynara_conformance.json'
    if args.diagnostic:
        filename = filename.replace('.json', '_diagnostic.json')
    if args.free_control:
        filename = filename.replace('.json', '_free_control.json')
    (out / filename).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

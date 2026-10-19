"""Offline generic registry decoder. Never treats registry names as verified ABI."""
import hashlib
import json
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from Crypto.Hash import keccak


def signature_selector(signature):
    if not isinstance(signature, str) or not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*\([A-Za-z0-9_,()\[\]]*\)', signature):
        return None
    digest = keccak.new(digest_bits=256, data=signature.encode('ascii')).hexdigest()
    return '0x' + digest[:8]


def decode(selector, pages):
    """Accept complete ordered raw HTTP pages with URL/status/time/SHA bindings.

    Each page carries url, status, retrieved_at, body (UTF8 string), body_sha256.
    The acquisition manifest must independently establish all-selector coverage;
    this function validates response integrity, not absence of selection bias.
    """
    output = {'selector': selector, 'decoded_name':'', 'signature':'', 'registry_id':None,
              'matching_signatures':0, 'verified_abi':False, 'status':'unavailable'}
    if not isinstance(selector,str) or not re.fullmatch(r'0x[0-9a-fA-F]{8}',selector):
        return output
    literal = selector.lower()
    if not pages:
        return output
    expected = None
    signatures = []
    total = None
    observed = 0
    seen_urls = set()
    try:
        for index,page in enumerate(pages):
            url = page['url']; parsed = urlparse(url)
            query = parse_qs(parsed.query)
            if (parsed.scheme != 'https' or parsed.netloc != 'www.4byte.directory'
                    or parsed.path != '/api/v1/signatures/' or query.get('hex_signature') != [literal]
                    or (index == 0 and query.get('page', ['1']) != ['1'])
                    or url in seen_urls or (index and url != expected) or page['status'] != 200):
                raise ValueError('response identity')
            seen_urls.add(url)
            stamp = datetime.fromisoformat(page['retrieved_at'].replace('Z','+00:00'))
            if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
                raise ValueError('UTC time required')
            body = page['body']
            if hashlib.sha256(body.encode('utf-8')).hexdigest() != page['body_sha256']:
                raise ValueError('body digest')
            data = json.loads(body)
            if not isinstance(data['count'],int) or isinstance(data['count'],bool) or data['count'] < 0:
                raise ValueError('count')
            if total is None:
                total = data['count']
            if total != data['count'] or not isinstance(data['results'],list):
                raise ValueError('pagination count')
            observed += len(data['results'])
            for entry in data['results']:
                identifier = entry.get('id'); signature = entry.get('text_signature')
                if (isinstance(identifier,int) and not isinstance(identifier,bool) and identifier >= 0
                        and signature_selector(signature) == literal):
                    signatures.append((identifier,signature))
            expected = data['next']
            if index < len(pages)-1 and not isinstance(expected,str):
                raise ValueError('excess pages')
        if expected is not None or observed != total:
            raise ValueError('incomplete pagination')
    except (KeyError,TypeError,ValueError,AttributeError,UnicodeError):
        output['status'] = 'invalid_response_binding'
        return output
    output['matching_signatures'] = len({signature for _,signature in signatures})
    if signatures:
        identifier,signature = min(signatures)
        output.update(decoded_name=signature.split('(',1)[0],signature=signature,
                      registry_id=identifier,status='generic_registry_match')
    return output

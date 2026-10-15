"""Research integrity boundaries, exercised independently of paid providers."""
import json
from urllib.parse import urlsplit

import pytest


def test_public_fallbacks_cannot_embed_private_quicknode_path_credentials():
    from faultseeker.utils.rpc_provider import _PUBLIC
    assert all(not (urlsplit(url).hostname.endswith('.quiknode.pro') and urlsplit(url).path.strip('/'))
               for endpoints in _PUBLIC.values() for url, _weight in endpoints)

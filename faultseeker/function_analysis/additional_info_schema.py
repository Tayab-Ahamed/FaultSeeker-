"""Pure additional-info request normalization before any evidence lookup.

A request is accepted atomically. Every function reference becomes an exact
20-byte address plus function string; unresolved aliases never become addresses.
This module performs no I/O and never resolves names or guesses missing fields.
"""
from __future__ import annotations
import re

ADDRESS = re.compile(r'0x[0-9a-fA-F]{40}\Z')
FUNCTION_FIELDS = frozenset(('function_call','children_calls','source_code'))
REQUEST_FIELDS = FUNCTION_FIELDS | {'balance_change'}


class AdditionalInfoSchemaError(ValueError):
    """Malformed model request; no part of it may enter evidence lookup."""


def _address(value, location):
    if not isinstance(value,str) or not ADDRESS.fullmatch(value):
        raise AdditionalInfoSchemaError(location + ': full 20-byte address required')
    return value.lower()


def _function(value, location):
    if (not isinstance(value,str) or not value.strip() or '::' in value
        or ADDRESS.fullmatch(value) or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise AdditionalInfoSchemaError(location + ': nonempty function name or selector required')
    return value.strip()


def normalize_function_reference(value, location='function reference'):
    """Normalize dictionary, documented (address,function), or exact :: string."""
    if isinstance(value,dict):
        if (set(value) not in ({'address','function'},{'address','function_name'})):
            raise AdditionalInfoSchemaError(location + ': expected only address and function/function_name')
        address=value['address'];function=value.get('function',value.get('function_name'))
    elif isinstance(value,(list,tuple)):
        if len(value)!=2:
            raise AdditionalInfoSchemaError(location + ': expected address/function pair')
        address,function=value
    elif isinstance(value,str):
        parts=value.split('::')
        if len(parts)!=2:
            raise AdditionalInfoSchemaError(location + ': expected unambiguous address/function reference')
        first_address=bool(ADDRESS.fullmatch(parts[0]));second_address=bool(ADDRESS.fullmatch(parts[1]))
        if first_address==second_address:
            raise AdditionalInfoSchemaError(location + ': exactly one full address required')
        address,function=parts if first_address else (parts[1],parts[0])
    else:
        raise AdditionalInfoSchemaError(location + ': unsupported function reference')
    return {'address':_address(address,location),'function':_function(function,location)}


def normalize_additional_info(request):
    """Validate all fields, then return new canonical lists without touching input.

    Reference collections are lists. The prior singleton source_code dictionary
    is accepted and normalized to a one-item list. Empty requests/lists are valid
    explicit no-op requests; unknown keys or unresolved addresses reject all data.
    """
    if not isinstance(request,dict) or set(request)-REQUEST_FIELDS:
        raise AdditionalInfoSchemaError('Additional-info request must contain only supported fields')
    normalized={}
    for field,value in request.items():
        if field=='balance_change':
            if not isinstance(value,list):
                raise AdditionalInfoSchemaError('balance_change: address list required')
            normalized[field]=[_address(address,'balance_change['+str(i)+']') for i,address in enumerate(value)]
        else:
            if field=='source_code' and isinstance(value,dict):value=[value]
            if not isinstance(value,list):
                raise AdditionalInfoSchemaError(field + ': function reference list required')
            normalized[field]=[normalize_function_reference(reference,field+'['+str(i)+']') for i,reference in enumerate(value)]
    return normalized

"""Pure observed prompt call identities; never infer owners from selectors.

Incoming entry functions and direct child callees are distinct facts. Preserve
actual code addresses under delegation and every observed parent occurrence.
"""
import re
ADDRESS=re.compile(r'0x[0-9a-fA-F]{40}\Z')

def _address(value):
    if not isinstance(value,str) or not ADDRESS.fullmatch(value):
        raise ValueError('Observed call reference requires a full address')
    return value.lower()

def _function(value):
    if not isinstance(value,str) or not value.strip() or value!=value.strip():
        raise ValueError('Observed function must be a nonblank exact string')
    return value

def _depth(value):
    if not isinstance(value,(list,tuple)) or any(type(i) is not int or i<0 for i in value):
        raise ValueError('Observed call depth must be a nonnegative index path')
    return list(value)

def observed_call_references(address,function_name,address_calls,trace):
    """Return incoming entry functions and actual direct-child call references.

    This returns fresh dictionaries and explicit empty lists. A bare selector
    is never accepted as an address, and DELEGATECALL children keep their actual
    callee implementation instead of borrowing their parent's storage owner.
    """
    owner=_address(address);requested=_function(function_name)
    if not isinstance(address_calls,dict):raise ValueError('Observed address-function mapping required')
    incoming=[];seen=set()
    for actual_owner,functions in address_calls.items():
        # Only this owner's incoming entries belong in the prompt section.
        if not isinstance(actual_owner,str) or actual_owner.lower()!=owner:continue
        _address(actual_owner)
        if not isinstance(functions,(list,tuple)):raise ValueError('Observed incoming function list required')
        for function in functions:
            function=_function(function)
            if function not in seen:
                incoming.append({'address':owner,'function':function});seen.add(function)
    roots=trace if isinstance(trace,list) else [trace] if isinstance(trace,dict) else None
    if roots is None:raise ValueError('Legacy trace root or list required')
    children=[]
    def walk(node,path):
        if not isinstance(node,dict):raise ValueError('Observed trace node required')
        function=node.get('function');node_address=node.get('address')
        node_type=node.get('type','call')
        call=node_type in ('call','CALL','create','CREATE','CREATE2')
        if function is not None and function!='' and call:
            actual=_address(node_address);function=_function(function)
            parent_path=_depth(node['depth']) if 'depth' in node else list(path)
            if actual==owner and function==requested:
                for index,child in enumerate(node.get('children',[])):
                    if not isinstance(child,dict):raise ValueError('Observed child node required')
                    child_fn=child.get('function')
                    if child.get('type','call') not in ('call','CALL','create','CREATE','CREATE2') or child_fn is None or child_fn=='':continue
                    callee=_address(child.get('address'));child_fn=_function(child_fn)
                    raw_type=child.get('call_type')
                    if raw_type is not None and not isinstance(raw_type,str):raise ValueError('Observed call type must be a string')
                    child_path=_depth(child['depth']) if 'depth' in child else list(path+(index,))
                    children.append({'address':callee,'function':child_fn,'call_type':raw_type,
                                     'depth':child_path,'parent_depth':parent_path})
        descendants=node.get('children',[])
        if not isinstance(descendants,list):raise ValueError('Observed children must be a list')
        for i,child in enumerate(descendants):walk(child,path+(i,))
    for i,root in enumerate(roots):walk(root,(i,))
    return {'observed_entry_functions_at_address':incoming,'observed_child_calls':children}

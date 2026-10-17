"""Small, source-only Solidity signature checks for Batch C.

The checker deliberately does not compile Solidity.  It lexes enough of a
source file to identify externally callable function declarations, local
``struct`` definitions, and local contract/interface names, then applies the
ABI spelling rules needed by the candidate rows.  An imported name is never
treated as resolved merely because it looks like a Solidity type.

Public API::

    canonical_signature(declaration, struct_definitions=None) -> str
    signature_in_source(signature, text) -> bool
    validate_target(signature, declaration_text, full_source) -> True

Run the self-contained offline tests with::

    python -B reports/new_batches/batchC/source_checks.py --self-test
"""
from __future__ import annotations

import argparse
import re
import unittest
from dataclasses import dataclass
from typing import Iterable, Mapping

__all__ = [
    "canonical_signature",
    "signature_in_source",
    "validate_target",
    "validate_evidence",
]


class _SignatureError(ValueError):
    """Internal spelling of a source/signature validation failure."""


@dataclass(frozen=True)
class _Token:
    value: str
    start: int
    end: int


@dataclass(frozen=True)
class _Scope:
    name: str
    start: int
    end: int


@dataclass(frozen=True)
class _Struct:
    name: str
    fields: tuple[tuple[_Token, ...], ...]


_IDENT = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_NUMBER = re.compile(r"[0-9][0-9_]*")
_DATA_LOCATIONS = {"memory", "calldata", "storage"}
_PARAM_QUALIFIERS = _DATA_LOCATIONS | {"indexed"}
_VISIBILITY = {"external", "public"}
_PRIMITIVE = {
    "address",
    "bool",
    "string",
    "bytes",
    "byte",
}


def _fail(message: str) -> None:
    raise _SignatureError(message)


def _tokenize(text: str) -> list[_Token]:
    """Tokenize Solidity while ignoring comments and quoted strings.

    Comments are skipped character by character rather than with a regular
    expression, so ``//`` and ``/*`` inside a string literal do not terminate
    or consume source unexpectedly.  Strings are skipped as well: a function
    word inside a string is not a declaration.
    """
    if not isinstance(text, str):
        _fail("Solidity source must be text")
    tokens: list[_Token] = []
    i, length = 0, len(text)
    while i < length:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "/" and i + 1 < length and text[i + 1] == "/":
            i += 2
            while i < length and text[i] not in "\r\n":
                i += 1
            continue
        if ch == "/" and i + 1 < length and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            if end < 0:
                _fail("unterminated block comment")
            i = end + 2
            continue
        if ch in "\"'":
            quote = ch
            i += 1
            while i < length:
                if text[i] == "\\":
                    i += 2
                elif text[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
            else:
                _fail("unterminated string literal")
            continue
        match = _IDENT.match(text, i)
        if match:
            tokens.append(_Token(match.group(), i, match.end()))
            i = match.end()
            continue
        match = _NUMBER.match(text, i)
        if match:
            tokens.append(_Token(match.group(), i, match.end()))
            i = match.end()
            continue
        # Solidity's declaration grammar only needs punctuation here.  Keep
        # every character as a token so malformed constructs fail closed.
        tokens.append(_Token(ch, i, i + 1))
        i += 1
    return tokens


def _matching(tokens: list[_Token], opening: int, left: str = "(", right: str = ")") -> int:
    if opening >= len(tokens) or tokens[opening].value != left:
        _fail(f"expected {left}")
    depth = 0
    for index in range(opening, len(tokens)):
        value = tokens[index].value
        if value == left:
            depth += 1
        elif value == right:
            depth -= 1
            if depth == 0:
                return index
    _fail(f"unclosed {left}{right} group")


def _split_top_level(tokens: Iterable[_Token], separator: str = ",") -> list[tuple[_Token, ...]]:
    pieces: list[tuple[_Token, ...]] = []
    current: list[_Token] = []
    parens = brackets = braces = 0
    for token in tokens:
        value = token.value
        if value == "(":
            parens += 1
        elif value == ")":
            parens -= 1
        elif value == "[":
            brackets += 1
        elif value == "]":
            brackets -= 1
        elif value == "{":
            braces += 1
        elif value == "}":
            braces -= 1
        if value == separator and not (parens or brackets or braces):
            if not current:
                _fail("empty declaration component")
            pieces.append(tuple(current))
            current = []
        else:
            current.append(token)
        if min(parens, brackets, braces) < 0:
            _fail("unbalanced declaration punctuation")
    if current:
        pieces.append(tuple(current))
    elif pieces:
        _fail("trailing declaration separator")
    return pieces


def _brace_pairs(tokens: list[_Token]) -> dict[int, int]:
    stack: list[int] = []
    pairs: dict[int, int] = {}
    for index, token in enumerate(tokens):
        if token.value == "{":
            stack.append(index)
        elif token.value == "}":
            if not stack:
                _fail("unbalanced braces")
            opening = stack.pop()
            pairs[opening] = index
    if stack:
        _fail("unclosed brace")
    return pairs


class _Model:
    """Local type declarations and lexical contract/interface scopes."""

    def __init__(self, tokens: list[_Token]):
        self.tokens = tokens
        self.pairs = _brace_pairs(tokens)
        self.scopes: list[_Scope] = []
        self.contracts: set[str] = set()
        self.structs: dict[str, _Struct] = {}
        self._build_scopes()
        self._build_structs()

    def _containing_scope(self, token_index: int) -> _Scope | None:
        choices = [scope for scope in self.scopes if scope.start < token_index < scope.end]
        return min(choices, key=lambda scope: scope.end - scope.start, default=None)

    def scope_name(self, token_index: int) -> str | None:
        scope = self._containing_scope(token_index)
        return scope.name if scope else None

    def _build_scopes(self) -> None:
        declarations: list[tuple[int, str, int]] = []
        for index, token in enumerate(self.tokens):
            if token.value not in {"contract", "interface", "library"}:
                continue
            if index + 1 >= len(self.tokens) or not _IDENT.fullmatch(self.tokens[index + 1].value):
                continue
            name = self.tokens[index + 1].value
            opening = index + 2
            while opening < len(self.tokens) and self.tokens[opening].value not in {"{", ";"}:
                opening += 1
            if opening >= len(self.tokens) or self.tokens[opening].value != "{":
                continue
            closing = self.pairs.get(opening)
            if closing is None:
                _fail(f"unclosed declaration for {name}")
            declarations.append((opening, name, closing))
        for opening, short_name, closing in sorted(declarations):
            parent = self._containing_scope(opening)
            full_name = f"{parent.name}.{short_name}" if parent else short_name
            scope = _Scope(full_name, opening, closing)
            self.scopes.append(scope)
            self.contracts.add(full_name)

    def _build_structs(self) -> None:
        for index, token in enumerate(self.tokens):
            if token.value != "struct" or index + 2 >= len(self.tokens):
                continue
            name_token = self.tokens[index + 1]
            if not _IDENT.fullmatch(name_token.value) or self.tokens[index + 2].value != "{":
                continue
            closing = self.pairs.get(index + 2)
            if closing is None:
                _fail(f"unclosed struct {name_token.value}")
            field_tokens = self.tokens[index + 3:closing]
            # Struct members conventionally end in semicolons; unlike a
            # parameter list, the final member's semicolon is not an empty
            # field and is therefore accepted here.
            if field_tokens and field_tokens[-1].value == ";":
                field_tokens = field_tokens[:-1]
            fields = tuple(_split_top_level(field_tokens, separator=";"))
            if not fields:
                _fail(f"struct {name_token.value} has no fields")
            scope = self._containing_scope(index)
            full_name = f"{scope.name}.{name_token.value}" if scope else name_token.value
            if full_name in self.structs:
                _fail(f"duplicate struct declaration {full_name}")
            self.structs[full_name] = _Struct(full_name, fields)

    def resolve_named(self, name: str, scope: str | None) -> tuple[str, str]:
        """Return (kind, fully-qualified name), rejecting unresolved names."""
        if "." in name:
            candidates = [name]
        else:
            candidates = []
            current = scope
            while current:
                candidates.append(f"{current}.{name}")
                current = current.rsplit(".", 1)[0] if "." in current else None
            candidates.append(name)
        for candidate in candidates:
            if candidate in self.structs:
                return "struct", candidate
            if candidate in self.contracts:
                return "contract", candidate
        # A short name is valid only if it identifies one local declaration.
        if "." not in name:
            matches = [key for key in (*self.structs.keys(), *self.contracts) if key.rsplit(".", 1)[-1] == name]
            if len(matches) == 1:
                kind = "struct" if matches[0] in self.structs else "contract"
                return kind, matches[0]
        _fail(f"unresolved local Solidity type: {name}")


def _model_from_definitions(definitions: str | Mapping[str, object] | None) -> _Model:
    if definitions is None:
        return _Model([])
    if isinstance(definitions, str):
        return _Model(_tokenize(definitions))
    if isinstance(definitions, Mapping):
        # This convenience form is intentionally source-like: values contain
        # complete struct bodies/declarations, rather than guessed ABI types.
        source_parts = []
        for key, value in definitions.items():
            if not isinstance(key, str) or not isinstance(value, str):
                _fail("struct_definitions mapping must contain text values")
            source_parts.append(value if re.search(r"\bstruct\b", value) else f"struct {key} {{ {value} }}")
        return _Model(_tokenize("\n".join(source_parts)))
    _fail("struct_definitions must be Solidity source text or a mapping")


def _parse_array_suffix(tokens: tuple[_Token, ...], index: int) -> tuple[str, int]:
    suffix = ""
    while index < len(tokens) and tokens[index].value == "[":
        close = _matching(list(tokens), index, "[", "]")
        inside = tokens[index + 1:close]
        if len(inside) > 1 or (inside and not _NUMBER.fullmatch(inside[0].value)):
            _fail("array length must be a literal integer")
        dimension = "" if not inside else inside[0].value.replace("_", "")
        suffix += f"[{dimension}]"
        index = close + 1
    return suffix, index


def _parse_type(tokens: tuple[_Token, ...], model: _Model, scope: str | None, *, field: bool = False) -> str:
    if not tokens:
        _fail("missing parameter type")
    index = 0
    if tokens[index].value == "mapping":
        _fail("mapping parameters are not ABI signature types")
    if tokens[index].value == "struct":
        index += 1
        if index >= len(tokens):
            _fail("missing struct type name")

    if tokens[index].value == "(":
        close = _matching(list(tokens), index)
        components = _split_top_level(tokens[index + 1:close])
        if not components:
            _fail("empty tuple type")
        base = "(" + ",".join(_parse_param(component, model, scope) for component in components) + ")"
        index = close + 1
    else:
        first = tokens[index].value
        if first == "address" and index + 1 < len(tokens) and tokens[index + 1].value == "payable":
            base = "address"
            index += 2
        elif first in _PRIMITIVE:
            base = "bytes1" if first == "byte" else first
            index += 1
        elif re.fullmatch(r"(?:u?int)(?:[0-9]+)?", first):
            unsigned = first.startswith("uint")
            width = first[4:] if unsigned else first[3:]
            if width and (int(width) < 8 or int(width) > 256 or int(width) % 8):
                _fail(f"invalid integer width: {first}")
            base = ("uint" if unsigned else "int") + (width or "256")
            index += 1
        elif re.fullmatch(r"bytes[0-9]+", first):
            width = int(first[5:])
            if not 1 <= width <= 32:
                _fail(f"invalid bytes width: {first}")
            base = first
            index += 1
        elif _IDENT.fullmatch(first):
            names = [first]
            index += 1
            while index + 1 < len(tokens) and tokens[index].value == "." and _IDENT.fullmatch(tokens[index + 1].value):
                names.extend((".", tokens[index + 1].value))
                index += 2
            kind, resolved = model.resolve_named("".join(names), scope)
            if kind == "contract":
                base = "address"
            else:
                base = "__struct__" + resolved
        else:
            _fail(f"unsupported parameter type: {first}")

    suffix, index = _parse_array_suffix(tokens, index)
    remaining = list(tokens[index:])
    # The remaining words are parameter name and data location.  They do not
    # enter an ABI signature, but rejecting punctuation/extra words prevents
    # an incomplete or invented declaration from passing.
    name_seen = False
    for token in remaining:
        value = token.value
        if value in _PARAM_QUALIFIERS:
            continue
        if _IDENT.fullmatch(value) and not name_seen:
            name_seen = True
            continue
        _fail(f"unexpected parameter token: {value}")
    if field and not name_seen:
        _fail("struct field is missing a name")
    return base + suffix


def _parse_param(tokens: tuple[_Token, ...], model: _Model, scope: str | None) -> str:
    return _parse_type(tokens, model, scope)


def _expand_struct(type_name: str, model: _Model, stack: tuple[str, ...]) -> str:
    if not type_name.startswith("__struct__"):
        return type_name
    name = type_name[len("__struct__"):]
    if name in stack:
        _fail(f"recursive struct cannot be canonicalized: {name}")
    definition = model.structs.get(name)
    if definition is None:
        _fail(f"unresolved struct definition: {name}")
    components = []
    for field in definition.fields:
        # Struct fields are semicolon-delimited and can contain a field name.
        components.append(_expand_type(_parse_type(field, model, name.rsplit(".", 1)[0] if "." in name else None, field=True), model, stack + (name,)))
    return "(" + ",".join(components) + ")"


def _expand_type(type_name: str, model: _Model, stack: tuple[str, ...] = ()) -> str:
    # Inline tuple components may themselves contain struct markers.  Expand
    # the tuple recursively before handling an array suffix.
    if type_name.startswith("("):
        depth = 0
        close = -1
        for index, char in enumerate(type_name):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    close = index
                    break
        if close < 0:
            _fail("unclosed canonical tuple")
        inner = type_name[1:close]
        parts = [] if not inner else _split_canonical_components(inner)
        suffix = type_name[close + 1:]
        return "(" + ",".join(_expand_type(part, model, stack) for part in parts) + ")" + suffix
    if "__struct__" not in type_name:
        return type_name
    # A struct marker can only be the base followed by array suffixes.
    marker_end = len(type_name)
    while marker_end > 0 and type_name[marker_end - 1] == "]":
        opening = type_name.rfind("[", 0, marker_end)
        if opening < 0:
            break
        marker_end = opening
    marker = type_name[:marker_end]
    suffix = type_name[marker_end:]
    return _expand_struct(marker, model, stack) + suffix


def _split_canonical_components(text: str) -> list[str]:
    """Split a generated tuple spelling without treating nested commas as separators."""
    parts: list[str] = []
    start = depth = 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            if index == start:
                _fail("empty canonical tuple component")
            parts.append(text[start:index])
            start = index + 1
    if depth or start == len(text):
        _fail("malformed canonical tuple")
    parts.append(text[start:])
    return parts


def _function_candidates(tokens: list[_Token], model: _Model, *, skip_invalid: bool = False) -> list[tuple[str, int, int]]:
    """Return (canonical signature, token start, token end) declarations."""
    candidates: list[tuple[str, int, int]] = []
    for index, token in enumerate(tokens):
        if token.value != "function" or index + 2 >= len(tokens):
            continue
        name = tokens[index + 1].value
        if not _IDENT.fullmatch(name) or tokens[index + 2].value != "(":
            continue
        close = _matching(tokens, index + 2)
        visibility = False
        conflicting_visibility = False
        end = close + 1
        parens = brackets = 0
        while end < len(tokens):
            value = tokens[end].value
            if value == "(":
                parens += 1
            elif value == ")":
                parens -= 1
            elif value == "[":
                brackets += 1
            elif value == "]":
                brackets -= 1
            elif not parens and not brackets and value in _VISIBILITY:
                visibility = True
            elif not parens and not brackets and value in {"internal", "private"}:
                conflicting_visibility = True
            if not parens and not brackets and value in {"{", ";"}:
                break
            end += 1
        if end == len(tokens) and not visibility:
            continue
        if not visibility or conflicting_visibility:
            continue
        scope = model.scope_name(index)
        params = _split_top_level(tokens[index + 3:close])
        if len(params) == 1 and not params[0]:
            params = []
        try:
            canonical_params = [_expand_type(_parse_param(param, model, scope), model) for param in params]
        except ValueError:
            if skip_invalid:
                continue
            raise
        candidates.append((f"{name}({','.join(canonical_params)})", index, end))
    return candidates


def _canonical_from_declaration(declaration: str, model: _Model) -> str:
    tokens = _tokenize(declaration)
    candidates = _function_candidates(tokens, model)
    if not candidates:
        _fail("no complete external/public function declaration found")
    if len(candidates) > 1:
        # A quote may include an interface heading and one function, but two
        # callable declarations make its target ambiguous.
        _fail("declaration text contains multiple external/public functions")
    return candidates[0][0]


def _canonical_declarations(declaration: str, model: _Model, *, skip_invalid: bool = False) -> list[str]:
    return [candidate[0] for candidate in _function_candidates(_tokenize(declaration), model, skip_invalid=skip_invalid)]


def canonical_signature(declaration: str, struct_definitions: str | Mapping[str, object] | None = None) -> str:
    """Return the canonical ABI signature for one typed external/public function.

    ``struct_definitions`` is optional Solidity source containing local type
    declarations.  If a declaration uses a struct or contract/interface type,
    that type must be present in this source (or in the declaration text when
    it contains the definition); unresolved imported names raise ``ValueError``.
    """
    if not isinstance(declaration, str) or not declaration.strip():
        _fail("declaration must be non-empty text")
    declaration_model = _model_from_definitions(struct_definitions)
    # Definitions occasionally appear in the exact quote alongside the
    # function.  Build one model so global and namespaced structs resolve.
    if re.search(r"\b(?:struct|contract|interface|library)\b", declaration):
        source = declaration if struct_definitions is None else declaration + "\n" + (struct_definitions if isinstance(struct_definitions, str) else "")
        declaration_model = _Model(_tokenize(source))
    return _canonical_from_declaration(declaration, declaration_model)


def _expected_signature(signature: str) -> str:
    if not isinstance(signature, str) or not signature.strip():
        _fail("signature must be non-empty text")
    # Parsing as a declaration also canonicalizes uint/int and inline tuples.
    return canonical_signature("function " + signature.strip() + " external")


def signature_in_source(signature: str, text: str) -> bool:
    """Return whether ``text`` contains a local external/public declaration."""
    try:
        expected = _expected_signature(signature)
        tokens = _tokenize(text)
        model = _Model(tokens)
        return any(candidate[0] == expected for candidate in _function_candidates(tokens, model, skip_invalid=True))
    except ValueError:
        return False


def validate_target(signature: str, declaration_text: str, full_source: str) -> bool:
    """Validate a row's signature and exact declaration against full source.

    The declaration must itself be complete and external/public, and its
    canonical form must occur in the supplied full source.  This rejects
    private/internal functions, raw-selector-only evidence, and imported type
    names with no local declaration.
    """
    if not isinstance(full_source, str) or not full_source.strip():
        _fail("full_source must be non-empty Solidity source")
    expected = _expected_signature(signature)
    source_tokens = _tokenize(full_source)
    model = _Model(source_tokens)
    declared = _canonical_declarations(declaration_text, model, skip_invalid=True)
    if expected not in declared:
        _fail(f"canonical signature mismatch: expected {expected}, got {declared}")
    if not any(candidate[0] == expected for candidate in _function_candidates(source_tokens, model, skip_invalid=True)):
        _fail("target declaration is not source-resolved as external/public")
    return True


def validate_evidence(signature: str, declaration_text: str, full_source: str) -> bool:
    """Compatibility helper for evidence records; equivalent to validate_target."""
    return validate_target(signature, declaration_text, full_source)


class _SelfTests(unittest.TestCase):
    def test_simple_normalization_and_comments(self):
        declaration = """function transfer(
            address payable recipient, /* ignored uint */ uint amount,
            int delta, uint[] memory values
        ) public returns (bool) { }"""
        self.assertEqual(
            canonical_signature(declaration),
            "transfer(address,uint256,int256,uint256[])",
        )

    def test_struct_tuple_arrays_and_namespace(self):
        source = """
        interface Router {
            struct Inner { address who; uint amount; }
            struct Outer {
                Inner[] items;
                bytes32 tag;
                Router.Inner one;
            }
            function route(Outer calldata item, Router.Inner[] memory many) external;
        }
        """
        expected = "route(((address,uint256)[],bytes32,(address,uint256)),(address,uint256)[])"
        self.assertEqual(canonical_signature("function route(Outer calldata item, Router.Inner[] memory many) external", source), expected)
        self.assertTrue(signature_in_source(expected, source))

    def test_struct_inside_inline_tuple(self):
        source = """
        struct Leaf { uint value; }
        contract C { function f((Leaf leaf, address who)[] calldata xs) external {} }
        """
        self.assertEqual(canonical_signature("function f((Leaf leaf, address who)[] calldata xs) external", source), "f(((uint256),address)[])")

    def test_local_contract_interface_types_are_addresses(self):
        source = """
        interface IERC20 {}
        contract Vault { function pull(IERC20 token, address payable to) public {} }
        """
        self.assertEqual(canonical_signature("function pull(IERC20 token, address payable to) public", source), "pull(address,address)")
        self.assertTrue(validate_target("pull(address,address)", "function pull(IERC20 token, address payable to) public", source))

    def test_unresolved_imported_type_fails_closed(self):
        source = 'import "./IERC20.sol"; contract Vault { function pull(IERC20 token) external {} }'
        with self.assertRaises(ValueError):
            validate_target("pull(address)", "function pull(IERC20 token) external", source)

    def test_visibility_and_mismatch(self):
        source = "contract C { function hidden(uint x) internal {} function open(uint x) external {} }"
        self.assertFalse(signature_in_source("hidden(uint256)", source))
        with self.assertRaises(ValueError):
            validate_target("hidden(uint256)", "function hidden(uint x) internal", source)
        with self.assertRaises(ValueError):
            validate_target("open(address)", "function open(uint x) external", source)

    def test_exact_multiline_quote(self):
        source = """
        // function fake(uint x) external;
        interface I {
            function receive(
                uint fromChainId, address to, uint nonce, uint volume,
                (address signatory, uint8 v, bytes32 r, bytes32 s)[] memory signatures
            ) virtual external payable;
        }
        """
        quote = """function receive(
            uint fromChainId, address to, uint nonce, uint volume,
            (address signatory, uint8 v, bytes32 r, bytes32 s)[] memory signatures
        ) virtual external payable;"""
        self.assertTrue(validate_target("receive(uint256,address,uint256,uint256,(address,uint8,bytes32,bytes32)[])", quote, source))
        self.assertFalse(signature_in_source("fake(uint256)", source))

    def test_comment_only_declaration_is_not_code(self):
        source = "// function fake(uint x) external;"
        with self.assertRaises(ValueError):
            validate_target("fake(uint256)", "function fake(uint x) external", source)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run offline unittest checks")
    args = parser.parse_args()
    if args.self_test:
        unittest.main(argv=[__file__], verbosity=2)
    else:
        parser.error("use --self-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

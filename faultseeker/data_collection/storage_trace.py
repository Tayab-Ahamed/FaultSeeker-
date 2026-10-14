"""Normalize geth-style opcode logs into storage reads and writes.

Opcode logs are observations, including writes later rolled back by REVERT.
The ``reverted`` flag preserves that provenance for downstream detectors.
"""

from __future__ import annotations

from typing import Any


CALL_OPS = {"CALL", "STATICCALL", "DELEGATECALL", "CALLCODE", "CREATE", "CREATE2"}
MUTATING_CALL_OPS = {"CALL", "DELEGATECALL", "CALLCODE", "CREATE", "CREATE2"}
REVERT_OPS = {"REVERT", "INVALID"}


def _word(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip().lower().removeprefix("0x")
    if not raw:
        raw = "0"
    try:
        number = int(raw, 16)
    except ValueError:
        return None
    if number < 0 or number >= 2**256:
        return None
    return f"0x{number:064x}"


def _address(value: Any) -> str | None:
    value = _word(value)
    return "0x" + value[-40:] if value else None


def _storage_value(storage: Any, slot: str | None) -> str | None:
    if not isinstance(storage, dict) or not slot:
        return None
    for key, value in storage.items():
        if _word(key) == slot:
            return _word(value)
    return None


def _canonical_frames(root: dict | None) -> dict[str, dict]:
    frames: dict[str, dict] = {}

    def walk(node: dict, call_id: str) -> None:
        frames[call_id] = node
        for index, child in enumerate(node.get("children", [])):
            walk(child, f"{call_id}.{index}")

    if isinstance(root, dict):
        walk(root, "0")
    return frames


def normalize_opcode_storage_trace(struct_logs: list[dict], root_trace: dict | None) -> dict[str, list[dict]]:
    """Return chronological ``storage_reads`` and ``storage_events`` from raw logs.

    A call frame owns storage at its callee for CALL/STATICCALL, and at its
    caller's storage address for DELEGATECALL/CALLCODE. Call IDs follow the
    executed opcode frame order and are cross-checked with a callTracer tree
    when one is available.
    """
    result: dict[str, list[dict]] = {"storage_reads": [], "storage_events": []}
    if not struct_logs or not isinstance(root_trace, dict):
        return result
    root_owner = str(root_trace.get("callee") or root_trace.get("to") or root_trace.get("address") or "").lower()
    if not root_owner:
        return result

    canonical = _canonical_frames(root_trace)
    frames = [{"owner": root_owner, "call_id": "0", "children": 0,
               "after_external": False, "reverted": False, "entries": [], "value_undo": {}}]
    observed_values: dict[tuple[str, str], str] = {}

    def finalize(frame: dict) -> None:
        reference = canonical.get(frame["call_id"], {})
        failed = frame["reverted"] or reference.get("success") is False
        if failed:
            for entry in frame["entries"]:
                entry["reverted"] = True
            for key, previous in frame['value_undo'].items():
                if previous is None:
                    observed_values.pop(key, None)
                else:
                    observed_values[key] = previous
        if frames:
            frames[-1]["entries"].extend(frame["entries"])
            if not failed:
                for key, previous in frame['value_undo'].items():
                    frames[-1]['value_undo'].setdefault(key, previous)

    for index, log in enumerate(struct_logs):
        try:
            depth = max(1, int(log.get("depth", 1)))
        except (TypeError, ValueError):
            depth = len(frames)
        while len(frames) > depth:
            finalize(frames.pop())
        # An unexplained depth jump cannot establish an accurate owner.
        if depth != len(frames):
            continue
        frame = frames[-1]
        op = str(log.get("op") or "").upper()
        stack = log.get("stack") or []
        owner = frame["owner"]
        if op in REVERT_OPS:
            frame["reverted"] = True
        if owner and op in {"SLOAD", "SSTORE"}:
            slot = _word(stack[-1]) if stack else None
            if slot:
                base = {"address": owner, "slot": slot, "pc": log.get("pc"),
                        "depth": depth, "call_id": frame["call_id"],
                        "event_index": index, "reverted": False}
                value_before = _storage_value(log.get("storage"), slot) or observed_values.get((owner, slot))
                if op == "SLOAD":
                    # With storage disabled, the following stack has SLOAD's result.
                    if value_before is None and index + 1 < len(struct_logs):
                        following = struct_logs[index + 1]
                        if following.get("depth") == depth and following.get("stack"):
                            value_before = _word(following["stack"][-1])
                    entry = {**base, "value": value_before}
                    result["storage_reads"].append(entry)
                    frame["entries"].append(entry)
                    if value_before is not None:
                        frame['value_undo'].setdefault((owner, slot), observed_values.get((owner, slot)))
                        observed_values[(owner, slot)] = value_before
                elif len(stack) >= 2:
                    value_after = _word(stack[-2])
                    entry = {**base, "value_before": value_before,
                             "value_after": value_after,
                             "after_external_call": frame["after_external"]}
                    result["storage_events"].append(entry)
                    frame["entries"].append(entry)
                    if value_after is not None:
                        frame['value_undo'].setdefault((owner, slot), observed_values.get((owner, slot)))
                        observed_values[(owner, slot)] = value_after

        next_depth = depth
        if index + 1 < len(struct_logs):
            try:
                next_depth = int(struct_logs[index + 1].get("depth", depth))
            except (TypeError, ValueError):
                pass
        if op in CALL_OPS and next_depth == depth + 1:
            call_id = f"{frame['call_id']}.{frame['children']}"
            frame["children"] += 1
            callee = _address(stack[-2]) if len(stack) >= 2 and op not in {"CREATE", "CREATE2"} else None
            canonical_node = canonical.get(call_id, {})
            if op in {"DELEGATECALL", "CALLCODE"}:
                child_owner = owner
            else:
                child_owner = (callee or canonical_node.get("callee") or canonical_node.get("to") or "").lower()
            external = op in {"DELEGATECALL", "CALLCODE"} or (child_owner and child_owner != owner)
            if op in MUTATING_CALL_OPS and external:
                frame["after_external"] = True
            frames.append({"owner": child_owner, "call_id": call_id, "children": 0,
                           "after_external": False, "reverted": False, "entries": [], "value_undo": {}})
    while len(frames) > 1:
        finalize(frames.pop())
    finalize(frames.pop())
    return result

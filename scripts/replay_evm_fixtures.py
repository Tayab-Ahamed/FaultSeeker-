"""Compile and replay local Solidity cases against an ephemeral Anvil chain.

No trace artifact is emitted unless solc compilation, deployment, transaction
execution, and both RPC trace calls all succeed. This runner never uses a
remote endpoint or a real private key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "tests" / "fixtures" / "contracts"
DEV_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def resolve_tools() -> tuple[dict[str, str], list[str]]:
    found = {}
    missing = []
    foundry_dir = os.getenv("FOUNDRY_BIN", "")
    for name, variable in (("solc", "SOLC_BINARY"), ("anvil", "ANVIL_BINARY"), ("cast", "CAST_BINARY")):
        candidate = os.getenv(variable) or (str(Path(foundry_dir) / name) if foundry_dir and name != "solc" else "")
        resolved = (candidate if candidate and Path(candidate).is_file() else shutil.which(candidate or name))
        if resolved:
            found[name] = str(resolved)
        else:
            missing.append(name)
    return found, missing


def _command(arguments: list[str], *, input_text: str | None = None) -> str:
    completed = subprocess.run(arguments, input=input_text, text=True,
                               capture_output=True, timeout=120, check=False)
    if completed.returncode:
        raise RuntimeError(f"{Path(arguments[0]).name} failed ({completed.returncode}): {completed.stderr.strip()}")
    return completed.stdout


def _json_output(text: str) -> dict:
    start = text.find("{")
    if start < 0:
        raise RuntimeError("command did not return JSON")
    return json.loads(text[start:])


def compile_contracts(solc: str) -> tuple[dict, dict]:
    sources = {path.name: {"content": path.read_text(encoding="utf-8")}
               for path in sorted(SOURCES.glob("*.sol"))}
    if len(sources) != 3:
        raise RuntimeError("expected all three Solidity fixture sources")
    standard_input = {"language": "Solidity", "sources": sources,
                      "settings": {"outputSelection": {"*": {"*": ["evm.bytecode.object"]}}}}
    output = _json_output(_command([solc, "--standard-json"], input_text=json.dumps(standard_input)))
    errors = [item for item in output.get("errors", []) if item.get("severity") == "error"]
    if errors:
        raise RuntimeError("solc compilation failed: " + "; ".join(item.get("formattedMessage", "") for item in errors))
    return output["contracts"], {
        name: hashlib.sha256(data["content"].encode()).hexdigest()
        for name, data in sources.items()
    }


def _rpc(url: str, method: str, params: list) -> object:
    request = Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1,
                                           "method": method, "params": params}).encode(),
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=15) as response:
        payload = json.load(response)
    if payload.get("error"):
        raise RuntimeError(f"{method}: {payload['error']}")
    return payload.get("result")


def _send(cast: str, url: str, target: str | None, signature: str | None = None,
          arguments: tuple[str, ...] = (), value: str | None = None,
          bytecode: str | None = None) -> dict:
    command = [cast, "send"]
    if bytecode is not None:
        command += ["--create", "0x" + bytecode]
    else:
        command += [target or "", signature or ""] + list(arguments)
    if value:
        command += ["--value", value]
    command += ["--json", "--rpc-url", url, "--private-key", DEV_KEY]
    receipt = _json_output(_command(command))
    if receipt.get("status") not in ("0x1", 1, "1"):
        raise RuntimeError(f"transaction reverted: {receipt.get('transactionHash')}")
    return receipt


def _bytecode(compiled: dict, source: str, contract: str) -> str:
    code = compiled[source][contract]["evm"]["bytecode"]["object"]
    if not code or "__" in code:
        raise RuntimeError(f"unlinked or empty bytecode: {contract}")
    return code


def _deploy(compiled: dict, cast: str, url: str, source: str, contract: str) -> str:
    receipt = _send(cast, url, None, bytecode=_bytecode(compiled, source, contract))
    address = receipt.get("contractAddress")
    if not address:
        raise RuntimeError(f"no contract address for {contract}")
    return address


def execute_cases(compiled: dict, cast: str, url: str) -> dict:
    vault = _deploy(compiled, cast, url, "ReentrancyCases.sol", "VulnerableVault")
    attacker = _deploy(compiled, cast, url, "ReentrancyCases.sol", "RecursiveAttacker")
    _send(cast, url, attacker, "setVault(address)", (vault,))
    _send(cast, url, vault, "deposit()", value="2ether")
    reentrant = _send(cast, url, attacker, "attack()", value="1ether")

    guard = _deploy(compiled, cast, url, "GuardCases.sol", "GuardedVault")
    guard_probe = _deploy(compiled, cast, url, "GuardCases.sol", "GuardProbe")
    _send(cast, url, guard_probe, "setVault(address)", (guard,))
    guarded = _send(cast, url, guard_probe, "attack()", value="1ether")

    implementation = _deploy(compiled, cast, url, "ProxyCases.sol", "ProxyImplementation")
    proxy = _deploy(compiled, cast, url, "ProxyCases.sol", "StorageProxy")
    _send(cast, url, proxy, "setImplementation(address)", (implementation,))
    delegated = _send(cast, url, proxy, "setValue(uint256)", ("42",))

    cases = {}
    for name, receipt in (("reentrant", reentrant), ("guarded", guarded), ("delegatecall", delegated)):
        tx = receipt["transactionHash"]
        call_trace = _rpc(url, "debug_traceTransaction", [tx, {"tracer": "callTracer"}])
        opcode_trace = _rpc(url, "debug_traceTransaction", [tx, {"disableMemory": True,
                                                                  "disableStack": False,
                                                                  "disableStorage": False}])
        if not isinstance(call_trace, dict) or not isinstance(opcode_trace, dict) or not isinstance(opcode_trace.get("structLogs"), list):
            raise RuntimeError(f"incomplete trace for {name}: {tx}")
        cases[name] = {"receipt": receipt, "call_trace": call_trace,
                       "opcode_trace": opcode_trace}
    return cases


def replay(output: Path, tools: dict[str, str], port: int = 18545) -> dict:
    compiled, source_hashes = compile_contracts(tools["solc"])
    url = f"http://127.0.0.1:{port}"
    server = subprocess.Popen([tools["anvil"], "--port", str(port), "--silent"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for _ in range(50):
            if server.poll() is not None:
                raise RuntimeError("anvil exited before accepting connections")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("anvil did not start")
        chain_id = _rpc(url, "eth_chainId", [])
        if chain_id != "0x7a69":
            raise RuntimeError(f"unexpected local chain ID: {chain_id}")
        cases = execute_cases(compiled, tools["cast"], url)
        artifact = {"status": "EXECUTED", "authentic_execution": True,
                    "chain_id": chain_id, "source_sha256": source_hashes,
                    "compiler": _command([tools["solc"], "--version"]).strip(),
                    "cases": cases}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
        return artifact
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="only check required local binaries")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "reports" / "local_evm_fixture_trace.json")
    args = parser.parse_args()
    tools, missing = resolve_tools()
    if missing:
        print(json.dumps({"status": "PENDING-TOOLS", "missing": missing,
                          "required_env": ["SOLC_BINARY", "ANVIL_BINARY", "CAST_BINARY", "FOUNDRY_BIN"]}))
        return 2
    if args.check:
        print(json.dumps({"status": "READY", "tools": tools}))
        return 0
    try:
        artifact = replay(args.output, tools)
        print(json.dumps({"status": artifact["status"], "output": str(args.output),
                          "cases": list(artifact["cases"])}))
        return 0
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(json.dumps({"status": "FAILED", "reason": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

# Threat Model

## Assets

- Correct exploit localization for finalized blockchain transactions.
- Integrity of transaction traces, token-flow evidence, contract source data, and benchmark labels.
- Analyst trust in confidence scores and evidence cards.

## Trust Assumptions

- Finalized chain history is canonical and cannot be altered by the adversary.
- Local code, benchmark scripts, and generated reports are trusted when run in a clean environment.
- RPC and explorer providers are not fully trusted; they can fail, omit trace features, rate-limit, or return inconsistent data.

## Adversary Capabilities

The adversary can:

- Use proxy contracts, delegatecalls, and implementation indirection.
- Obfuscate calldata and use misleading function names.
- Split exploit behavior across multiple transactions or blocks.
- Generate recursive/noisy traces to dilute signal quality.
- Emit fake or misleading events.
- Trigger explorer/WAF failures or rely on chains with limited trace support.
- Poison LLM-facing text fields such as decoded calldata, labels, or source comments.

The adversary cannot:

- Break base-chain consensus.
- Modify finalized transaction ordering or finalized logs.
- Tamper with locally pinned benchmark artifacts after reproducible download.

## Failure Assumptions

- Trace collection may fail or be partial.
- Source code may be unavailable or proxy-resolved incorrectly.
- LLM output may be malformed, overconfident, or vulnerable to prompt-like content in untrusted fields.
- Single-transaction analysis may miss multi-transaction campaigns.

## Required Robustness Evaluations

- Proxy obfuscation and delegatecall-heavy traces.
- Misleading function names and fake events.
- Recursive noise traces.
- Prompt-injection-like calldata or comments.
- Multi-transaction splitting and delayed profit extraction.

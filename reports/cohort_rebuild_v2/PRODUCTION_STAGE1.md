# Recorded inputs through production forensics

Command: `python scripts/run_train_production.py`.
Run: `20261015T150951-4a3803b0`.

Seven of ten frozen train identities completed the actual production sequencer,
TraceAnalyzer, SignalExtractor, rule classifier, address/fund-flow classifiers and
FunctionRanker. Only the network I/O input readers were replaced with hash-bound
recorded transaction, receipt and trace readers. Every socket connect was refused;
no outcome, signal, ranking or classifier result was mocked. Exact source bytes,
seed, config, observations and digests are in the run directory and outputs manifest.
The three records with no captured trace remain unavailable, not negatives.

The structured-trace production fallback now preserves observed CREATE/CREATE2
metadata and address/selector memos. RPC normalization is shared with the live
collector; contract creation uses the canonical receipt's created address.

Observed reentrancy component on seven cases: TP=3 FP=1 FN=0 TN=3,
precision 0.75, recall 1, F1 0.8571428571428571. All seven Stage1 rule verdicts
were EXPLOIT, but this exploit-only population cannot establish general precision.
The complete storage-aware detector is separately measured on four cases (one
positive, three negatives), F1 1.0, with six remaining train opcode gaps.

Coverage is not upgraded by offline conversion. Token-flow completeness and
multi-transaction completeness remain false where unproved. Stage2 model
analysis, Stage3 Eq.4 records, billed hybrid cost savings and source-linked function
localization were not executed by this command and remain unmeasured. No held-out
partition or final-exam permit was used. Claim30 remains UNVERIFIABLE for full
paper experiment reproduction, despite this working production replay path.

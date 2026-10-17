# Batch A control and diagnostic

Diagnostic only; no tuning; no new scoring claim.

## Control

Requested 10 original-110 controls; executed 4; blocked 6 due missing local full callTracer artifacts. Diagnosis: `adapter_control_failed`.

| Transaction | Known rank | Adapter rank | Reproduced |
|---|---:|---:|---|
| `0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb` | None | None | True |
| `0x958236266991bc3fe3b77feaacea120f172c0708ad01c7a715b255f218f9313c` | 19 | 27 | False |
| `0xa6f63fcb6bec8818864d96a5b1bb19e8bd85ee37b2cc916412e720988440b2aa` | 7 | None | False |
| `0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d` | None | 33 | False |

## Batch A classification counts

- `adapter_or_format_mismatch`: 21
- `label_in_trace_but_ranked_low`: 1
- `label_not_in_trace`: 1

## Format checks

- Address casing normalized-equivalent: 23/23
- Source checksum valid: 1/23
- Function selector resolved to labeled name: 1/23
- Function selector unresolved/mismatched where label address was called: 21/23
- Possible proxy/implementation signal: 0/23

## Examples

### adapter_or_format_mismatch
- `0x07887fffc4488354d813fdcca5da0586dd6f9a3da36d503af768302eacbeec41`: address_rank=2, function_rank=None, pair_rank=None, candidates=10, address_in_trace=True
- `0x2c9f87e285026601a2c8903cf5f10e5b3655fbd0264490c41514ce073c42a9c3`: address_rank=31, function_rank=None, pair_rank=None, candidates=32, address_in_trace=True
- `0x322592750691798488006a26aa042b55ab9d7637f9b0adc42089a4c480e51870`: address_rank=2, function_rank=None, pair_rank=None, candidates=10, address_in_trace=True

### label_in_trace_but_ranked_low
- `0x39328ea4377a8887d3f6ce91b2f4c6b19a851e2fc5163e2f83bbc2fc136d0c71`: address_rank=5, function_rank=9, pair_rank=13, candidates=18, address_in_trace=True

### label_not_in_trace
- `0x96bf6bd14a81cf19939c0b966389daed778c3a9528a6c5dd7a4d980dec966388`: address_rank=None, function_rank=None, pair_rank=None, candidates=4, address_in_trace=False
